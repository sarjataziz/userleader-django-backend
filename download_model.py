import gdown
import os

file_id = "1jFTayEKAzTltJkMeTNXgJcXi9-pbX4cZ"
url = f"https://drive.google.com/uc?id={file_id}"
output_path = "userleader_app/models/best_rf_model.pkl"

if not os.path.exists(output_path):
    print("Downloading model file...")
    try:
        gdown.download(url, output_path, quiet=False, fuzzy=True)
        print("Download complete!")
    except Exception as e:
        print(f"An error occurred: {e}")
else:
    print("Model file already exists.")
