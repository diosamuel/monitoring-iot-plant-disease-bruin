#!/usr/bin/env python3
"""
Simple Camera Image Server
Serves leaf.jpg on localhost:3000/
"""

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse
import uvicorn
import os

app = FastAPI()

@app.get("/")
async def serve_image():
    """Serve the leaf.jpg image."""
    image_path = "leaf.jpg"
    
    if not os.path.exists(image_path):
        return Response(
            content="Image file leaf.jpg not found",
            status_code=404,
            media_type="text/plain"
        )
    
    return FileResponse(
        image_path,
        media_type="image/jpeg",
        filename="leaf.jpg"
    )
    
uvicorn.run(app, host="localhost", port=3000)