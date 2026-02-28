import os
import json
import logging
import time
import requests
import html
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional

import app
import env_loader
from lib.thumbnail_task import ThumbnailGeneratorTask
from lib.fact_checker import cleanup_fact_references
from lib.affiliate_linker import add_affiliate_links

# Load environment
env_loader.load()

# Setup Logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "automation.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Automation")

STATUS_FILE = "automation_status.json"

class StatusManager:
    """Manages the persistence of processed posts to allow resuming."""
    def __init__(self, filename: str):
        self.filename = filename
        self.processed_ids = self._load()

    def _load(self) -> set:
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get("processed_ids", []))
            except Exception as e:
                logger.error(f"Failed to load status file: {e}")
        return set()

    def is_processed(self, entry_id: str) -> bool:
        return entry_id in self.processed_ids

    def mark_processed(self, entry_id: str):
        self.processed_ids.add(entry_id)
        self._save()

    def _save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump({"processed_ids": list(self.processed_ids)}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save status file: {e}")

class AutomatedBlogProcessor:
    def __init__(self):
        self.status_mgr = StatusManager(STATUS_FILE)
        self.blogs_config = app.load_blogs_config()
        self.thumb_task = ThumbnailGeneratorTask({"enabled": True})

    def run(self):
        logger.info("Starting automated blog processing batch...")
        
        for blog_id in self.blogs_config.keys():
            try:
                self.process_blog(blog_id)
            except Exception as e:
                logger.error(f"Critical error processing blog {blog_id}: {e}")

        logger.info("Batch processing complete.")

    def process_blog(self, blog_id: str):
        logger.info(f"--- Processing Blog: {blog_id} ---")
        
        # Fetch entries (AtomPub /entry returns recent posts including drafts)
        response, error = app.hatena_request(blog_id, '/entry')
        if error:
            logger.error(f"Failed to fetch posts for {blog_id}: {error}")
            return

        try:
            root = ET.fromstring(response.content)
            entries = root.findall('atom:entry', app.HATENA_NS)
            
            for entry in entries:
                self.process_entry(blog_id, entry)
                
        except ET.ParseError as e:
            logger.error(f"XML parse error for blog {blog_id}: {e}")

    def process_entry(self, blog_id: str, entry: ET.Element):
        entry_id_el = entry.find('atom:id', app.HATENA_NS)
        entry_id = entry_id_el.text if entry_id_el is not None else "unknown"
        
        if self.status_mgr.is_processed(entry_id):
            return

        title_el = entry.find('atom:title', app.HATENA_NS)
        title = title_el.text if title_el is not None else "(No Title)"
        
        # Check draft status
        is_draft = False
        app_control = entry.find('app:control', app.HATENA_NS)
        if app_control is not None:
            draft_el = app_control.find('app:draft', app.HATENA_NS)
            if draft_el is not None and draft_el.text == 'yes':
                is_draft = True
        
        logger.info(f"Processing Entry: {title} (Draft: {is_draft})")

        # Get content
        content_el = entry.find('atom:content', app.HATENA_NS)
        content = content_el.text if content_el is not None else ""
        
        # Get Edit Link
        edit_link = ''
        for link in entry.findall('atom:link', app.HATENA_NS):
            if link.get('rel') == 'edit':
                edit_link = link.get('href', '')
                break

        if not edit_link:
            logger.error(f"Edit link not found for {title}")
            return

        original_content = content
        
        try:
            # 1. Thumbnail
            if not content.strip().startswith("!["):
                logger.info("  Step 1: Adding thumbnail...")
                try:
                    result = self.thumb_task.execute({
                        "title": title,
                        "content": content
                    })
                    content = result.get("enhanced_content", content)
                except Exception as te:
                    logger.error(f"  Step 1 failed (Thumbnail): {te}. Skipping this step.")
            else:
                logger.debug("  Step 1: Thumbnail already exists, skipping.")

            # 2. Fact Check
            logger.info("  Step 2: Running fact check...")
            content = cleanup_fact_references(title, content)

            # 3. Affiliate Links
            logger.info("  Step 3: Adding affiliate links...")
            content = add_affiliate_links(title, content)

            # 4. Update if changed
            if content != original_content:
                logger.info(f"  Finalizing: Updating entry on Hatena...")
                self.update_hatena_entry(blog_id, edit_link, title, content, is_draft)
                logger.info(f"  Successfully processed and updated: {title}")
            else:
                logger.info(f"  No changes needed for: {title}")

            # Mark processed even if no changes, to avoid re-scanning
            self.status_mgr.mark_processed(entry_id)

        except Exception as e:
            logger.error(f"Error processing entry {title}: {e}", exc_info=True)

    def update_hatena_entry(self, blog_id: str, edit_link: str, title: str, content: str, is_draft: bool):
        hatena_id, api_key = app.get_blog_auth(blog_id)
        
        # Maintain original draft status
        draft_val = 'yes' if is_draft else 'no'
        
        escaped_title = html.escape(title)
        escaped_content = html.escape(content)
        escaped_hatena_id = html.escape(hatena_id)
        
        atom_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>{escaped_title}</title>
  <author><name>{escaped_hatena_id}</name></author>
  <content type="text/x-hatena-syntax">{escaped_content}</content>
  <app:control>
    <app:draft>{draft_val}</app:draft>
  </app:control>
</entry>"""
        
        xml_bytes = atom_xml.encode('utf-8')
        
        response = requests.put(
            edit_link,
            auth=(hatena_id, api_key),
            data=xml_bytes,
            headers={'Content-Type': 'application/atom+xml; charset=utf-8'},
            timeout=30
        )
        response.raise_for_status()

if __name__ == "__main__":
    processor = AutomatedBlogProcessor()
    processor.run()
