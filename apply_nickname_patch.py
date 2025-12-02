import os

print("📁 Current Working Directory:", os.getcwd())
print("\n📂 Listing files in CWD:")
print(os.listdir("."))

print("\n📂 Listing files in project root (/):")
print(os.listdir("/"))

print("\n📂 Listing files in /app:")
try:
    print(os.listdir("/app"))
except:
    print("❌ /app does not exist")

print("\n📂 Listing files in /workspace:")
try:
    print(os.listdir("/workspace"))
except:
    print("❌ /workspace does not exist")

print("\n--- پایان بررسی ---")
