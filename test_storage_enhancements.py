import os
import json
import numpy as np
import datetime
from app.storage import UserManager

def test_storage():
    db_file = "test_users.json"
    if os.path.exists(db_file):
        os.remove(db_file)
        
    um = UserManager(db_file)
    
    # Test Registration
    print("Testing Registration...")
    encoding = np.array([0.1, 0.2, 0.3])
    um.register_user("TestUser", encoding, "Fist")
    
    # Reload and check
    um2 = UserManager(db_file)
    user_data = um2.users["TestUser"]
    
    print(f"Registered User Data: {user_data}")
    
    assert "last_registered" in user_data
    assert user_data["last_registered"] != "Unknown"
    assert "last_verified" in user_data
    assert user_data["last_verified"] == "Never"
    
    # Test Verification Update
    print("Testing Verification Update...")
    um2.update_last_verified("TestUser")
    
    # Reload again
    um3 = UserManager(db_file)
    user_data_updated = um3.users["TestUser"]
    
    print(f"Updated User Data: {user_data_updated}")
    
    assert user_data_updated["last_verified"] != "Never"
    # Check if it looks like a date
    try:
        datetime.datetime.strptime(user_data_updated["last_verified"], "%Y-%m-%d %H:%M:%S")
        print("Date format correct.")
    except ValueError:
        print("Date format INCORRECT.")
        return False

    print("Storage Tests Passed!")
    
    if os.path.exists(db_file):
        os.remove(db_file)
        
    return True

if __name__ == "__main__":
    test_storage()
