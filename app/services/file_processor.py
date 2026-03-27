"""
Service for parsing LAS and CSV petrophysical files.
Extracts metadata, curves and loads data into the database.
"""
import os
import uuid
import logging
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.petrophysical_file import PetrophysicalFile, CurveData, FileStatus, FileType
from app.models.well import Well

logger = logging.getLogger(__name__)

# Standard null values used in LAS files
NULL_VALUES = [-9999, -9999.0, -9999.25, -999.25, -999.0]


def save_upload_file(file_content: bytes, original_filename: str, well_id: int) -> Tuple[str, str]:
    """Save uploaded file to disk, return (filename, filepath)."""
    ext = Path(original_filename).suffix.lower()
    unique_filename = f"well_{well_id}_{uuid.uuid4().hex[:8]}{ext}"
    well_dir = os.path.join(settings.UPLOAD_DIR, f"well_{well_id}")
    os.makedirs(well_dir, exist_ok=True)
    filepath = os.path.join(well_dir, unique_filename)
    with open(filepath, "wb") as f:
        f.write(file_content)
    return unique_filename, filepath


def validate_file_extension(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in [e.lower() for e in settings.allowed_extensions_list]


def validate_file_size(size_bytes: int) -> bool:
    return size_bytes <= settings.max_file_size_bytes


def _replace_nulls(series: pd.Series, null_value: float = -9999.25) -> pd.Series:
    """Replace LAS null values with NaN."""
    mask = series.isin(NULL_VALUES)
    if null_value not in NULL_VALUES:
        mask |= (series == null_value)
    return series.where(~mask, other=np.nan)


def parse_las_file(filepath: str) -> Dict[str, Any]:
    """Parse a LAS file using lasio. Returns metadata and DataFrame."""
    try:
        import lasio
        las = lasio.read(filepath, ignore_header_errors=True)
    except Exception as e:
        raise ValueError(f"Impossible de lire le fichier LAS: {e}")

    # Extract header metadata
    def get_header(key: str) -> Optional[str]:
        try:
            val = las.well[key].value
            return str(val).strip() if val and str(val).strip() not in ["", "--", "N/A"] else None
        except Exception:
            return None

    metadata = {
        "well_name_in_file": get_header("WELL") or get_header("WN"),
        "company": get_header("COMP"),
        "field_in_file": get_header("FLD") or get_header("FIELD"),
        "location": get_header("LOC"),
        "country_in_file": get_header("CTRY") or get_header("COUNTRY"),
        "date_in_file": get_header("DATE"),
        "service_company": get_header("SRVC"),
        "start_depth": las.well.STRT.value if hasattr(las.well, "STRT") else None,
        "stop_depth": las.well.STOP.value if hasattr(las.well, "STOP") else None,
        "step": las.well.STEP.value if hasattr(las.well, "STEP") else None,
        "depth_unit": str(las.well.STRT.unit).strip() if hasattr(las.well, "STRT") else "M",
        "null_value": las.well.NULL.value if hasattr(las.well, "NULL") else -9999.25,
    }

    # Extract curves info
    available_curves = [c.mnemonic for c in las.curves if c.mnemonic.upper() not in ["DEPT", "DEPTH", "MD"]]
    curve_units = {c.mnemonic: str(c.unit).strip() for c in las.curves}

    # Convert to DataFrame
    df = las.df().reset_index()
    df.columns = [c.upper() for c in df.columns]

    # Identify depth column
    depth_col = next((c for c in df.columns if c in ["DEPT", "DEPTH", "MD"]), df.columns[0])
    df = df.rename(columns={depth_col: "DEPTH"})

    # Replace null values
    null_val = metadata.get("null_value", -9999.25)
    for col in df.columns:
        if col != "DEPTH":
            df[col] = _replace_nulls(df[col], null_val)

    return {
        "metadata": metadata,
        "available_curves": available_curves,
        "curve_units": curve_units,
        "df": df,
    }


def parse_csv_file(filepath: str) -> Dict[str, Any]:
    """Parse a CSV petrophysical file. Assumes first column is depth."""
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise ValueError(f"Impossible de lire le fichier CSV: {e}")

    df.columns = [c.upper().strip() for c in df.columns]

    # Detect depth column
    depth_candidates = ["DEPTH", "DEPT", "MD", "DEPTH_M", "PROFONDEUR"]
    depth_col = next((c for c in depth_candidates if c in df.columns), df.columns[0])
    df = df.rename(columns={depth_col: "DEPTH"})

    # Replace common null values
    df = df.replace(NULL_VALUES, np.nan)

    available_curves = [c for c in df.columns if c != "DEPTH"]
    curve_units = {c: "" for c in available_curves}
    start = float(df["DEPTH"].min()) if not df["DEPTH"].empty else None
    stop = float(df["DEPTH"].max()) if not df["DEPTH"].empty else None

    metadata = {
        "start_depth": start,
        "stop_depth": stop,
        "step": None,
        "depth_unit": "M",
        "null_value": None,
    }

    return {
        "metadata": metadata,
        "available_curves": available_curves,
        "curve_units": curve_units,
        "df": df,
    }


def process_file(db: Session, file_record: PetrophysicalFile) -> None:
    """
    Main processing function: parse file, save curves to DB.
    Called after file upload (can be run async via Celery).
    """
    try:
        file_record.status = FileStatus.PROCESSING
        db.commit()

        # Parse based on file type
        if file_record.file_type == FileType.LAS:
            result = parse_las_file(file_record.file_path)
        else:
            result = parse_csv_file(file_record.file_path)

        metadata = result["metadata"]
        df: pd.DataFrame = result["df"]
        available_curves = result["available_curves"]
        curve_units = result["curve_units"]

        # Update file record with metadata
        for key, value in metadata.items():
            if hasattr(file_record, key) and value is not None:
                setattr(file_record, key, value)

        file_record.available_curves = available_curves
        file_record.curve_units = curve_units

        # Delete old curve data for this file (replacement)
        db.query(CurveData).filter(CurveData.file_id == file_record.id).delete()

        # Insert curve data in bulk
        batch_size = 5000
        rows = []
        for _, row in df.iterrows():
            depth = row.get("DEPTH")
            if pd.isna(depth):
                continue
            for curve in available_curves:
                if curve not in df.columns:
                    continue
                val = row.get(curve)
                rows.append({
                    "file_id": file_record.id,
                    "well_id": file_record.well_id,
                    "curve_name": curve,
                    "depth_m": float(depth),
                    "value": float(val) if not pd.isna(val) else None,
                    "unit": curve_units.get(curve, ""),
                })
                if len(rows) >= batch_size:
                    db.bulk_insert_mappings(CurveData, rows)
                    db.flush()
                    rows = []

        if rows:
            db.bulk_insert_mappings(CurveData, rows)

        file_record.status = FileStatus.PROCESSED
        db.commit()
        logger.info(f"File {file_record.id} processed: {len(available_curves)} curves extracted")

    except Exception as e:
        logger.error(f"Error processing file {file_record.id}: {e}")
        file_record.status = FileStatus.ERROR
        file_record.error_message = str(e)[:500]
        db.commit()
        raise
