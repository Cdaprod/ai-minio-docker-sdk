from fastapi import FastAPI, HTTPException, BackgroundTasks
from minio import Minio
from docker import from_env as docker_from_env
import uvicorn
import tempfile
import uuid
import os

app = FastAPI()

# Configure MinIO client
minio_client = Minio(
    "play.min.io:443",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=True
)

# Configure Docker client
docker_client = docker_from_env()

@app.post("/execute/{bucket_name}/{script_name}")
async def execute_script(background_tasks: BackgroundTasks, bucket_name: str, script_name: str):
    script_path = None  # Initialize script_path outside of try block for broader scope
    try:
        # Retrieve script from MinIO
        response = minio_client.get_object(bucket_name, script_name)
        script_content = response.read().decode('utf-8')

        # Create a temporary file to store the script
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as script_file:
            script_file.write(script_content.encode())
            script_path = script_file.name  # Save the path for later use

        # Generate a unique identifier for the container
        container_name = f"script_execution_{uuid.uuid4()}"

        # Execute the script inside a Docker container
        container = docker_client.containers.run(
            image="python:3.8-slim",
            command=f"python {script_path}",
            volumes={os.path.dirname(script_path): {'bind': '/app', 'mode': 'rw'}},
            detach=True,
            remove=True,
            name=container_name
        )

        # Placeholder for background task to stream logs
        # background_tasks.add_task(stream_docker_logs, container, script_name)

        return {"message": "Execution started", "container_name": container_name}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Ensure the temporary file is removed after execution
        if script_path and os.path.exists(script_path):
            os.remove(script_path)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)