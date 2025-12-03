#!/usr/bin/env python3
"""
Log cleanup and archival script.
Archives logs older than a specified number of days and removes very old archives.
"""
import os
import sys
import gzip
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path


def get_log_dir() -> Path:
    """Get the logs directory path"""
    script_dir = Path(__file__).parent.parent
    return script_dir / "logs"


def archive_old_logs(log_dir: Path, days_old: int = 7) -> int:
    """
    Compress log files older than specified days.
    Returns count of archived files.
    """
    archived = 0
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    for log_file in log_dir.glob("*.log"):
        # Check file modification time
        
        # Check file modification time
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        if mtime < cutoff_date:
            # Compress the file
            archive_name = f"{log_file.name}.{mtime.strftime('%Y%m%d')}.gz"
            archive_path = log_dir / archive_name
            archive_name = f"{log_file.stem}.{mtime.strftime('%Y%m%d_%H%M%S')}.gz"
            archive_path = log_dir / archive_name
            
            with open(log_file, 'rb') as f_in:
                with gzip.open(archive_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Verify the archive was created successfully
            if not archive_path.exists() or archive_path.stat().st_size == 0:
                print(f"ERROR: Failed to create archive for {log_file.name}")
                if archive_path.exists():
                    archive_path.unlink()
                return archived
            
            # Clear the original file (don't delete, just truncate)
            log_file.write_text("")
            archived += 1
    
    return archived


def remove_old_archives(log_dir: Path, days_old: int = 30) -> int:
    """
    Remove archive files older than specified days.
    Returns count of removed files.
    """
    removed = 0
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    for archive_file in log_dir.glob("*.gz"):
        mtime = datetime.fromtimestamp(archive_file.stat().st_mtime)
        if mtime < cutoff_date:
            try:
                print(f"Removing old archive: {archive_file.name}")
                archive_file.unlink()
                removed += 1
            except Exception as e:
                print(f"ERROR: Failed to remove {archive_file.name}: {e}")
    
    return removed


def get_log_stats(log_dir: Path) -> dict:
    """Get statistics about log files"""
    stats = {
        "total_files": 0,
        "total_size_mb": 0,
        "log_files": [],
        "archive_files": [],
    }
    
    for file in log_dir.iterdir():
        if file.is_file():
            try:
                size_mb = file.stat().st_size / (1024 * 1024)
                stats["total_files"] += 1
                stats["total_size_mb"] += size_mb
                
                file_info = {
                    "name": file.name,
                    "size_mb": round(size_mb, 2),
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                }
                
                if file.suffix == ".gz":
                    stats["archive_files"].append(file_info)
                else:
                    stats["log_files"].append(file_info)
            except Exception as e:
                print(f"WARNING: Failed to stat {file.name}: {e}")
    
    stats["total_size_mb"] = round(stats["total_size_mb"], 2)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Log cleanup and archival utility")
    args = parser.parse_args()

    if args.archive_days >= args.remove_days:
        parser.error("--archive-days must be less than --remove-days")
        "--archive-days", 
        type=int, 
        default=7,
        help="Archive logs older than this many days (default: 7)"
    )
    parser.add_argument(
        "--remove-days",
        type=int,
        default=30,
        help="Remove archives older than this many days (default: 30)"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, don't perform cleanup"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    
    args = parser.parse_args()
    
    log_dir = get_log_dir()
    
    if not log_dir.exists():
        print(f"Log directory not found: {log_dir}")
        sys.exit(1)
    
    print(f"Log directory: {log_dir}")
    print("=" * 50)
    
    # Show stats
    stats = get_log_stats(log_dir)
    print(f"Total files: {stats['total_files']}")
    print(f"Total size: {stats['total_size_mb']} MB")
    print(f"Log files: {len(stats['log_files'])}")
    print(f"Archive files: {len(stats['archive_files'])}")
    print()
    
    if args.stats_only:
        print("Log files:")
        for f in stats["log_files"]:
            print(f"  {f['name']}: {f['size_mb']} MB (modified: {f['modified']})")
        print("\nArchive files:")
        for f in stats["archive_files"]:
            print(f"  {f['name']}: {f['size_mb']} MB (modified: {f['modified']})")
        return
    
    if args.dry_run:
        print("[DRY RUN] Would perform the following actions:")
        print(f"  - Archive logs older than {args.archive_days} days")
        print(f"  - Remove archives older than {args.remove_days} days")
        return
    
    # Perform cleanup
    print(f"Archiving logs older than {args.archive_days} days...")
    archived = archive_old_logs(log_dir, args.archive_days)
    print(f"Archived {archived} files")
    
    print(f"\nRemoving archives older than {args.remove_days} days...")
    removed = remove_old_archives(log_dir, args.remove_days)
    print(f"Removed {removed} files")
    
    print("\nCleanup complete!")


if __name__ == "__main__":
    main()
