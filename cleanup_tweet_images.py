#!/usr/bin/env python3
"""
Standalone Tweet Image Cleanup Script
Cleans up old tweet images to prevent disk space buildup
"""

import os
import sys
import glob
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def cleanup_tweet_images(base_dir: str = ".", days_to_keep: int = 7, dry_run: bool = False):
    """
    Clean up tweet images older than specified days.
    
    Args:
        base_dir: Base directory to search for images
        days_to_keep: Number of days to keep images (default: 7)
        dry_run: If True, only show what would be deleted without actually deleting
    """
    try:
        base_path = Path(base_dir)
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        cutoff_timestamp = cutoff_time.timestamp()
        
        # Directories to clean
        image_dirs = [
            base_path / "enhanced_tweet_images",
            base_path / "tweet_images",  # Legacy directory
        ]
        
        total_cleaned = 0
        total_size_saved = 0
        
        for image_dir in image_dirs:
            if not image_dir.exists():
                continue
                
            logging.info(f"Checking directory: {image_dir}")
            
            # Clean main directory
            image_patterns = ["*.png", "*.jpg", "*.jpeg"]
            
            for pattern in image_patterns:
                for image_file in image_dir.glob(pattern):
                    try:
                        file_stat = image_file.stat()
                        if file_stat.st_mtime < cutoff_timestamp:
                            file_size = file_stat.st_size
                            
                            if dry_run:
                                logging.info(f"[DRY RUN] Would delete: {image_file} ({file_size} bytes)")
                            else:
                                image_file.unlink()
                                logging.info(f"Deleted: {image_file} ({file_size} bytes)")
                            
                            total_cleaned += 1
                            total_size_saved += file_size
                            
                    except Exception as e:
                        logging.error(f"Error processing {image_file}: {str(e)}")
            
            # Clean branded tags subdirectory
            branded_tags_dir = image_dir / 'branded_tags'
            if branded_tags_dir.exists():
                for image_file in branded_tags_dir.glob("*.png"):
                    try:
                        # Don't delete the rotation counter file
                        if image_file.name == '.rotation_counter':
                            continue
                            
                        file_stat = image_file.stat()
                        if file_stat.st_mtime < cutoff_timestamp:
                            file_size = file_stat.st_size
                            
                            if dry_run:
                                logging.info(f"[DRY RUN] Would delete branded tag: {image_file} ({file_size} bytes)")
                            else:
                                image_file.unlink()
                                logging.info(f"Deleted branded tag: {image_file} ({file_size} bytes)")
                            
                            total_cleaned += 1
                            total_size_saved += file_size
                            
                    except Exception as e:
                        logging.error(f"Error processing {image_file}: {str(e)}")
        
        # Format file size
        if total_size_saved > 1024 * 1024:
            size_str = f"{total_size_saved / (1024 * 1024):.1f} MB"
        elif total_size_saved > 1024:
            size_str = f"{total_size_saved / 1024:.1f} KB"
        else:
            size_str = f"{total_size_saved} bytes"
        
        if dry_run:
            logging.info(f"[DRY RUN] Would clean up {total_cleaned} files, saving {size_str}")
        else:
            if total_cleaned > 0:
                logging.info(f"✅ Cleaned up {total_cleaned} old image files, saved {size_str}")
            else:
                logging.info(f"✅ No old images to clean up (older than {days_to_keep} days)")
                
    except Exception as e:
        logging.error(f"Error during image cleanup: {str(e)}")
        return False
    
    return True

def main():
    """Main entry point with command line argument support."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up old tweet images')
    parser.add_argument('--days', type=int, default=7, 
                       help='Number of days to keep images (default: 7)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--dir', type=str, default='.',
                       help='Base directory to search (default: current directory)')
    
    args = parser.parse_args()
    
    print(f"🧹 Tweet Image Cleanup")
    print(f"📁 Directory: {os.path.abspath(args.dir)}")
    print(f"📅 Keeping files newer than: {args.days} days")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be deleted")
    print("-" * 50)
    
    success = cleanup_tweet_images(
        base_dir=args.dir,
        days_to_keep=args.days,
        dry_run=args.dry_run
    )
    
    if success:
        print("✅ Cleanup completed successfully!")
    else:
        print("❌ Cleanup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 