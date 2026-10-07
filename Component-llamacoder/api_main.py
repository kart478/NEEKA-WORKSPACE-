import uvicorn

from neeka.api import create_app
from neeka.api.config import Settings


app = create_app()


if __name__ == "__main__":
    settings = Settings()
    uvicorn.run("api_main:app", host=settings.api_host, port=settings.api_port, reload=False)