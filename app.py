from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel, field_validator
from typing import Optional, List, Union
import os
import uuid
import asyncio
from datetime import datetime
from supabase import create_client, Client
import mimetypes
from pathlib import Path

# Initialize FastAPI app
app = FastAPI(title="Image Management System", version="1.0.0")

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Supabase configuration
SUPABASE_URL = "https://gbkhkbfbarsnpbdkxzii.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdia2hrYmZiYXJzbnBiZGt4emlpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQzODAzNzMsImV4cCI6MjA0OTk1NjM3M30.mcOcC2GVEu_wD3xNBzSCC3MwDck3CIdmz4D8adU-bpI"

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Pydantic models with flexible ID handling
class EstiloResponse(BaseModel):
    id: Union[str, int]  # Handle both strings and integers
    nombre: str
    
    @field_validator('id')
    @classmethod
    def convert_id_to_string(cls, v):
        return str(v)

class ColorResponse(BaseModel):
    id: Union[str, int]  # Handle both strings and integers
    color: str
    count: int
    terex1: str
    
    @field_validator('id')
    @classmethod
    def convert_id_to_string(cls, v):
        return str(v)

class ImageUploadResponse(BaseModel):
    id: Union[str, int]  # Handle both strings and integers
    estilo_id: Union[str, int]  # Handle both strings and integers
    color_id: Union[str, int]  # Handle both strings and integers
    file_name: str
    file_path: str
    public_url: str
    description: Optional[str]
    content_type: str
    file_size: int
    created_at: str
    
    @field_validator('id', 'estilo_id', 'color_id')
    @classmethod
    def convert_ids_to_string(cls, v):
        return str(v)

# Utility functions
def ceroadd_estilo(estilo_id: Union[str, int]) -> str:
    """Add leading zeros to estilo ID"""
    try:
        num = int(estilo_id) if isinstance(estilo_id, str) else estilo_id
        if num < 10:
            return f"0000{num}"
        elif num < 100:
            return f"000{num}"
        else:
            return f"00{num}"
    except (ValueError, TypeError):
        return str(estilo_id)

def ceroadd_color(color_id: Union[str, int]) -> str:
    """Add leading zeros to color ID"""
    try:
        num = int(color_id) if isinstance(color_id, str) else color_id
        if num < 10:
            return f"00{num}"
        elif num < 100:
            return f"0{num}"
        else:
            return str(num)
    except (ValueError, TypeError):
        return str(color_id)

# API Routes

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Main page - Style and Color selection"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/estilos", response_model=List[EstiloResponse])
async def get_estilos(search: Optional[str] = Query(None)):
    """Get estilos with prioridad=1, optionally filtered by search term"""
    supabase = get_supabase_client()
    
    try:
        query = supabase.table('inventario_estilos').select('id, nombre').eq('prioridad', 1).order('nombre')
        
        response = query.execute()
        estilos = response.data
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            estilos = [
                estilo for estilo in estilos 
                if search_lower in estilo['nombre'].lower() or search in str(estilo['id'])
            ]
        
        # Convert IDs to strings for consistent handling
        for estilo in estilos:
            estilo['id'] = str(estilo['id'])
        
        return estilos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching estilos: {str(e)}")

@app.get("/api/colores/{estilo_id}", response_model=List[ColorResponse])
async def get_colores(estilo_id: Union[str, int], search: Optional[str] = Query(None)):
    """Get colors available for a specific estilo with positive terex1 values"""
    supabase = get_supabase_client()
    
    try:
        # Get inventory items for the specific estilo with terex1 > 0
        inventario_query = supabase.table('inventario1').select('color_id, terex1').eq('estilo_id', estilo_id).gt('terex1', 0)
        inventario_response = inventario_query.execute()
        
        if not inventario_response.data:
            return []
        
        # Get unique color_ids and calculate stats
        color_stats = {}
        for item in inventario_response.data:
            color_id = str(item['color_id'])  # Convert to string for consistent handling
            terex1 = item['terex1'] or 0
            
            if color_id not in color_stats:
                color_stats[color_id] = {
                    'count': 1,
                    'terex1_total': terex1,
                }
            else:
                color_stats[color_id]['count'] += 1
                color_stats[color_id]['terex1_total'] += terex1
        
        # Get color details
        color_ids = list(color_stats.keys())
        if not color_ids:
            return []
            
        colors_query = supabase.table('inventario_colores').select('id, color').in_('id', color_ids)
        colors_response = colors_query.execute()
        
        # Build final response
        colors_list = []
        for color in colors_response.data:
            color_id = str(color['id'])  # Convert to string for consistent handling
            if color_id in color_stats:  # Make sure we have stats for this color
                stats = color_stats[color_id]
                avg_terex1 = stats['terex1_total'] / stats['count']
                
                colors_list.append({
                    'id': color_id,
                    'color': color['color'],
                    'count': stats['count'],
                    'terex1': f"{avg_terex1:.1f}"
                })
        
        # Sort by color name
        colors_list.sort(key=lambda x: x['color'])
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            colors_list = [
                color for color in colors_list 
                if search_lower in color['color'].lower() or search in str(color['id'])
            ]
        
        return colors_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching colors: {str(e)}")

@app.get("/upload/{estilo_id}/{color_id}", response_class=HTMLResponse)
async def upload_page(request: Request, estilo_id: Union[str, int], color_id: Union[str, int]):
    """Image upload page"""
    supabase = get_supabase_client()
    
    try:
        # Get estilo and color details
        estilo_response = supabase.table('inventario_estilos').select('nombre').eq('id', estilo_id).single().execute()
        color_response = supabase.table('inventario_colores').select('color').eq('id', color_id).single().execute()
        
        context = {
            "request": request,
            "estilo_id": str(estilo_id),
            "color_id": str(color_id),
            "estilo_nombre": estilo_response.data['nombre'],
            "color_nombre": color_response.data['color']
        }
        
        return templates.TemplateResponse("upload.html", context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading upload page: {str(e)}")

@app.post("/api/upload", response_model=dict)
async def upload_image(
    estilo_id: Union[str, int] = Form(...),
    color_id: Union[str, int] = Form(...),
    description: Optional[str] = Form(""),
    file: UploadFile = File(...)
):
    """Upload an image file"""
    supabase = get_supabase_client()
    
    try:
        # Convert IDs to strings for consistent handling
        estilo_id = str(estilo_id)
        color_id = str(color_id)
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Generate unique filename
        timestamp = int(datetime.now().timestamp() * 1000)
        file_extension = Path(file.filename).suffix.lower()
        if not file_extension:
            file_extension = '.jpg'  # default extension
        
        filename = f"image_{timestamp}{file_extension}"
        file_path = f"estilo_{estilo_id}/color_{color_id}/{filename}"
        
        # Upload to Supabase Storage
        storage_response = supabase.storage.from_('image-fundas').upload(
            path=file_path,
            file=file_content,
            file_options={"cache-control": "3600", "upsert": False}
        )
        
        if storage_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")
        
        # Get public URL
        public_url = supabase.storage.from_('image-fundas').get_public_url(file_path)
        
        # Save record to database
        db_response = supabase.table('image_uploads').insert({
            'estilo_id': estilo_id,
            'color_id': color_id,
            'file_name': file.filename,
            'file_path': file_path,
            'public_url': public_url,
            'description': description.strip() if description else None,
            'content_type': file.content_type,
            'file_size': file_size,
        }).execute()
        
        return {
            "success": True,
            "message": "Image uploaded successfully",
            "data": db_response.data[0]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")

@app.get("/api/images/{estilo_id}/{color_id}", response_model=List[ImageUploadResponse])
async def get_images(estilo_id: Union[str, int], color_id: Union[str, int]):
    """Get existing images for a specific estilo and color combination"""
    supabase = get_supabase_client()
    
    try:
        # Convert IDs to strings for consistent handling
        estilo_id = str(estilo_id)
        color_id = str(color_id)
        
        response = supabase.table('image_uploads').select('*').eq('estilo_id', estilo_id).eq('color_id', color_id).order('created_at', desc=True).execute()
        
        # Convert all IDs to strings for consistent handling
        for image in response.data:
            image['id'] = str(image['id'])
            image['estilo_id'] = str(image['estilo_id'])
            image['color_id'] = str(image['color_id'])
        
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching images: {str(e)}")

@app.delete("/api/images/{image_id}")
async def delete_image(image_id: Union[str, int]):
    """Delete an image and its record"""
    supabase = get_supabase_client()
    
    try:
        # Convert ID to string for consistent handling
        image_id = str(image_id)
        
        # Get image record first
        image_response = supabase.table('image_uploads').select('*').eq('id', image_id).single().execute()
        
        if not image_response.data:
            raise HTTPException(status_code=404, detail="Image not found")
        
        image_data = image_response.data
        file_path = image_data['file_path']
        
        # Delete from storage
        storage_response = supabase.storage.from_('image-fundas').remove([file_path])
        
        # Delete from database
        db_response = supabase.table('image_uploads').delete().eq('id', image_id).execute()
        
        return {
            "success": True,
            "message": "Image deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting image: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
