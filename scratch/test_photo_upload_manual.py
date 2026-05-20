import asyncio
import io
from starlette.datastructures import UploadFile
from fastapi import HTTPException
from app.main import update_user_profile, upload_client_photo

async def test_update_user_profile_limits():
    print("Testing update_user_profile limit...")
    
    # 1. Test photo under 500KB (e.g., 400KB)
    small_data = b"a" * (400 * 1024)
    file_small = UploadFile(
        filename="test_small.png",
        file=io.BytesIO(small_data),
        size=len(small_data),
        headers={"content-type": "image/png"}
    )
    
    try:
        # We expect a KeyError or other database error (since we didn't mock db), but NOT the 500KB limit exception
        await update_user_profile(
            photo=file_small,
            current_user={"email": "test@example.com", "role": "admin"}
        )
    except HTTPException as e:
        if "less than 500KB" in str(e.detail):
            print("[-] Failed: 400KB photo was incorrectly rejected by user profile update.")
            return False
    except Exception as e:
        # DB connection error or KeyError is expected and means it passed the size check
        pass
    
    print("[+] 400KB photo passed size check successfully.")

    # 2. Test photo over 500KB (e.g., 600KB)
    large_data = b"a" * (600 * 1024)
    file_large = UploadFile(
        filename="test_large.png",
        file=io.BytesIO(large_data),
        size=len(large_data),
        headers={"content-type": "image/png"}
    )
    
    try:
        await update_user_profile(
            photo=file_large,
            current_user={"email": "test@example.com", "role": "admin"}
        )
        print("[-] Failed: 600KB photo was not rejected by user profile update.")
        return False
    except HTTPException as e:
        if e.status_code == 400 and "less than 500KB" in e.detail:
            print("[+] 600KB photo was correctly rejected with: ", e.detail)
        else:
            print(f"[-] Failed: Unexpected HTTPException details: {e.status_code} - {e.detail}")
            return False
    except Exception as e:
        print(f"[-] Failed: Unexpected exception: {e}")
        return False
        
    return True

async def test_upload_client_photo_limits():
    print("\nTesting upload_client_photo limit...")
    
    # 1. Test photo under 500KB (e.g., 400KB)
    small_data = b"a" * (400 * 1024)
    file_small = UploadFile(
        filename="test_small.png",
        file=io.BytesIO(small_data),
        size=len(small_data),
        headers={"content-type": "image/png"}
    )
    
    try:
        await upload_client_photo(
            client_id="test_client",
            file=file_small,
            current_user={"email": "test@example.com", "role": "admin"}
        )
    except HTTPException as e:
        if "less than 500KB" in str(e.detail):
            print("[-] Failed: 400KB photo was incorrectly rejected by client photo upload.")
            return False
    except Exception as e:
        # DB connection error or KeyError is expected and means it passed the size check
        pass
        
    print("[+] 400KB photo passed size check successfully.")

    # 2. Test photo over 500KB (e.g., 600KB)
    large_data = b"a" * (600 * 1024)
    file_large = UploadFile(
        filename="test_large.png",
        file=io.BytesIO(large_data),
        size=len(large_data),
        headers={"content-type": "image/png"}
    )
    
    try:
        await upload_client_photo(
            client_id="test_client",
            file=file_large,
            current_user={"email": "test@example.com", "role": "admin"}
        )
        print("[-] Failed: 600KB photo was not rejected by client photo upload.")
        return False
    except HTTPException as e:
        if e.status_code == 400 and "less than 500KB" in e.detail:
            print("[+] 600KB photo was correctly rejected with: ", e.detail)
        else:
            print(f"[-] Failed: Unexpected HTTPException details: {e.status_code} - {e.detail}")
            return False
    except Exception as e:
        print(f"[-] Failed: Unexpected exception: {e}")
        return False
        
    return True

async def main():
    success1 = await test_update_user_profile_limits()
    success2 = await test_upload_client_photo_limits()
    if success1 and success2:
        print("\nAll size limit checks passed successfully!")
    else:
        print("\nSome checks failed.")

if __name__ == "__main__":
    asyncio.run(main())
