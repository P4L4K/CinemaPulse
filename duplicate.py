"""
DynamoDB Cleanup Script - Removes Duplicate Movies and Analytics

This script:
1. Scans all movies in the movies table
2. Finds duplicates (same name)
3. Keeps only the first occurrence
4. Deletes duplicates along with their analytics entries

IMPORTANT: Update AWS credentials/region before running!
"""

import boto3
from botocore.exceptions import ClientError

# Configure your AWS region
REGION = "us-east-1"

dynamodb = boto3.resource("dynamodb", region_name=REGION)

# DynamoDB Tables
movies_table = dynamodb.Table("CinemaPulse-Movies")
analytics_table = dynamodb.Table("CinemaPulse-Analytics")

def cleanup_duplicates():
    """Remove duplicate movies and their analytics"""
    
    print("=" * 60)
    print("CINEMAPULSE DUPLICATE CLEANUP")
    print("=" * 60)
    
    # Step 1: Scan all movies
    print("\n[1] Scanning all movies...")
    movies_response = movies_table.scan()
    all_movies = movies_response.get("Items", [])
    
    print(f"Found {len(all_movies)} total movies")
    
    if not all_movies:
        print("No movies to clean up!")
        return
    
    # Step 2: Find duplicates by movie name
    print("\n[2] Finding duplicates by name...")
    movies_by_name = {}
    duplicates_to_delete = []
    
    for movie in all_movies:
        movie_name = movie.get("name", "Unknown")
        movie_id = movie.get("id")
        
        if movie_name not in movies_by_name:
            # First occurrence - keep this one
            movies_by_name[movie_name] = {
                "id": movie_id,
                "first": True
            }
            print(f"  ✓ Keeping: {movie_name} (ID: {movie_id})")
        else:
            # Duplicate - mark for deletion
            duplicates_to_delete.append({
                "id": movie_id,
                "name": movie_name
            })
            print(f"  ✗ DUPLICATE: {movie_name} (ID: {movie_id})")
    
    if not duplicates_to_delete:
        print("\n✓ No duplicates found!")
        return
    
    print(f"\n[3] Found {len(duplicates_to_delete)} duplicates to delete")
    
    # Step 3: Delete duplicates
    print("\n[4] Deleting duplicates...")
    deleted_count = 0
    failed_count = 0
    
    for duplicate in duplicates_to_delete:
        movie_id = duplicate["id"]
        movie_name = duplicate["name"]
        
        try:
            # Delete from movies table
            movies_table.delete_item(Key={"id": movie_id})
            print(f"  ✓ Deleted movie: {movie_name}")
            
            # Delete from analytics table
            try:
                analytics_table.delete_item(Key={"movie_id": movie_id})
                print(f"    ✓ Deleted analytics for: {movie_name}")
            except ClientError as e:
                print(f"    ⚠ Analytics not found (OK): {movie_name}")
            
            deleted_count += 1
            
        except ClientError as e:
            print(f"  ✗ ERROR deleting {movie_name}: {str(e)}")
            failed_count += 1
    
    # Step 4: Verify cleanup
    print("\n[5] Verifying cleanup...")
    verify_response = movies_table.scan()
    remaining_movies = verify_response.get("Items", [])
    
    print(f"Total movies after cleanup: {len(remaining_movies)}")
    print("\nRemaining movies:")
    for movie in remaining_movies:
        print(f"  • {movie.get('name')} (Rating: {movie.get('rating')})")
    
    # Summary
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    print(f"Duplicates deleted: {deleted_count}")
    print(f"Failed deletions: {failed_count}")
    print(f"Movies remaining: {len(remaining_movies)}")
    print("=" * 60)

if __name__ == "__main__":
    try:
        cleanup_duplicates()
        print("\n✓ Cleanup completed successfully!")
    except Exception as e:
        print(f"\n✗ Error during cleanup: {str(e)}")
        print("Make sure your AWS credentials are configured correctly.")
