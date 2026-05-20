from database import users_collection
from schemas import UserRole

def check_admins():
    admins = list(users_collection.find({"role": UserRole.ADMIN}))
    count = len(admins)
    
    print(f"\n--- Admin Account Check ---")
    print(f"Total Admins Found: {count}")
    
    if count > 0:
        print("\nExisting Admin Emails:")
        for admin in admins:
            print(f"- {admin.get('email')}")
        print("\nNOTE: The '/init-super-admin' endpoint is BLOCKED as long as at least ONE admin exists.")
    else:
        print("\nNo admins found. You can now use '/init-super-admin'.")

if __name__ == "__main__":
    check_admins()
