from huggingface_hub import HfApi, HfFolder

api = HfApi()
token = HfFolder.get_token()

model_path = './userleader_app/models/best_rf_model.pkl'
repo_id = 'sarjat/best_rf_model'

api.upload_file(
    path_or_fileobj=model_path,
    path_in_repo="best_rf_model.pkl",
    repo_id=repo_id,
    repo_type="model",
    token=token
)
