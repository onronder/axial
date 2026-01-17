#!/usr/bin/env python3
"""
Quick diagnostic script to check YouTube ingestion status in the database.
Run from backend directory: python scripts/check_youtube_ingestion.py
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.db import get_supabase


def check_recent_youtube_jobs():
    """Check recent YouTube/web ingestion jobs and their status."""
    supabase = get_supabase()
    
    print("\n" + "="*80)
    print("🔍 RECENT INGESTION JOBS (last 10)")
    print("="*80)
    
    # Get recent ingestion jobs
    jobs = supabase.table("ingestion_jobs")\
        .select("*")\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()
    
    for job in jobs.data or []:
        print(f"\n📦 Job ID: {job['id']}")
        print(f"   Provider: {job.get('provider')}")
        print(f"   Status: {job.get('status')}")
        print(f"   Total Files: {job.get('total_files')}")
        print(f"   Processed: {job.get('processed_files')}")
        print(f"   Error: {job.get('error_message') or 'None'}")
        print(f"   Created: {job.get('created_at')}")
    
    print("\n" + "="*80)
    print("🔍 RECENT FILE STATUS (last 20) - Shows individual file processing")
    print("="*80)
    
    # Get recent file status entries
    file_status = supabase.table("ingestion_file_status")\
        .select("*")\
        .order("created_at", desc=True)\
        .limit(20)\
        .execute()
    
    for fs in file_status.data or []:
        status_icon = "✅" if fs.get('status') == 'completed' else "❌" if fs.get('status') == 'failed' else "⏳"
        print(f"\n{status_icon} File: {fs.get('file_name', 'Unknown')[:50]}")
        print(f"   Status: {fs.get('status')}")
        print(f"   Error: {fs.get('error_message') or 'None'}")
        print(f"   Job ID: {fs.get('job_id')}")
    
    print("\n" + "="*80)
    print("🔍 RECENT YOUTUBE DOCUMENTS (source_type = 'youtube')")
    print("="*80)
    
    # Check for YouTube documents specifically
    youtube_docs = supabase.table("documents")\
        .select("id, title, source_type, created_at")\
        .eq("source_type", "youtube")\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()
    
    if youtube_docs.data:
        for doc in youtube_docs.data:
            print(f"\n🎥 {doc.get('title', 'Untitled')[:60]}")
            print(f"   ID: {doc['id']}")
            print(f"   Created: {doc.get('created_at')}")
    else:
        print("\n⚠️  No YouTube documents found in the database!")
    
    print("\n" + "="*80)
    print("🔍 RECENT WEB DOCUMENTS (source_type = 'web')")
    print("="*80)
    
    # Check for web documents
    web_docs = supabase.table("documents")\
        .select("id, title, source_type, created_at")\
        .eq("source_type", "web")\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()
    
    if web_docs.data:
        for doc in web_docs.data:
            print(f"\n🌐 {doc.get('title', 'Untitled')[:60]}")
            print(f"   ID: {doc['id']}")
            print(f"   Created: {doc.get('created_at')}")
    else:
        print("\n⚠️  No web documents found in the database!")
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    # Count totals
    total_docs = supabase.table("documents").select("id", count="exact").execute()
    youtube_count = supabase.table("documents").select("id", count="exact").eq("source_type", "youtube").execute()
    web_count = supabase.table("documents").select("id", count="exact").eq("source_type", "web").execute()
    
    print(f"Total Documents: {total_docs.count}")
    print(f"YouTube Documents: {youtube_count.count}")
    print(f"Web Documents: {web_count.count}")


if __name__ == "__main__":
    check_recent_youtube_jobs()
