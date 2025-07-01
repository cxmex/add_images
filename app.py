from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Union
import os
import logging
from supabase import create_client, Client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Image Management System", version="1.0.0")

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gbkhkbfbarsnpbdkxzii.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdia2hrYmZiYXJzbnBiZGt4emlpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzQzODAzNzMsImV4cCI6MjA0OTk1NjM3M30.mcOcC2GVEu_wD3xNBzSCC3MwDck3CIdmz4D8adU-bpI")

logger.info(f"Starting app with Supabase URL: {SUPABASE_URL}")

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Models
class EstiloResponse(BaseModel):
    id: str
    nombre: str

@app.get("/")
async def root():
    """Root endpoint that also serves as health check"""
    try:
        logger.info("Root endpoint called")
        
        # Test database connection
        supabase = get_supabase_client()
        response = supabase.table('inventario_estilos').select('id').limit(1).execute()
        
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Image Management System</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 40px; 
                    background: #f5f5f5; 
                }
                .container { 
                    max-width: 800px; 
                    margin: 0 auto; 
                    background: white; 
                    padding: 40px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .status { 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                }
                .success { 
                    background: #d4edda; 
                    border: 1px solid #c3e6cb; 
                    color: #155724; 
                }
                .loading { 
                    background: #fff3cd; 
                    border: 1px solid #ffeaa7; 
                    color: #856404; 
                }
                button {
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    margin: 10px 5px;
                }
                button:hover { background: #0056b3; }
                pre { 
                    background: #f8f9fa; 
                    padding: 15px; 
                    border-radius: 5px; 
                    overflow-x: auto; 
                    max-height: 300px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Image Management System</h1>
                <div id="status" class="status loading">
                    ✅ System is running! Database connection successful.
                </div>
                
                <h2>API Endpoints:</h2>
                <button onclick="testEstilos()">Test /api/estilos</button>
                <button onclick="testHealth()">Test /health</button>
                <button onclick="testColors()">Test /api/colores/136</button>
                
                <div id="results"></div>
            </div>
            
            <script>
                async function testEstilos() {
                    try {
                        const response = await fetch('/api/estilos');
                        const data = await response.json();
                        document.getElementById('results').innerHTML = 
                            '<h3>✅ Estilos API Works!</h3><pre>' + 
                            JSON.stringify(data.slice(0, 5), null, 2) + '</pre>';
                    } catch (error) {
                        document.getElementById('results').innerHTML = 
                            '<h3 style="color: red">❌ Estilos API Error</h3><pre>' + error + '</pre>';
                    }
                }
                
                async function testHealth() {
                    try {
                        const response = await fetch('/health');
                        const data = await response.json();
                        document.getElementById('results').innerHTML = 
                            '<h3>✅ Health Check Works!</h3><pre>' + 
                            JSON.stringify(data, null, 2) + '</pre>';
                    } catch (error) {
                        document.getElementById('results').innerHTML = 
                            '<h3 style="color: red">❌ Health Check Error</h3><pre>' + error + '</pre>';
                    }
                }
                
                async function testColors() {
                    try {
                        const response = await fetch('/api/colores/136');
                        const data = await response.json();
                        document.getElementById('results').innerHTML = 
                            '<h3>✅ Colors API Works!</h3><pre>' + 
                            JSON.stringify(data.slice(0, 3), null, 2) + '</pre>';
                    } catch (error) {
                        document.getElementById('results').innerHTML = 
                            '<h3 style="color: red">❌ Colors API Error</h3><pre>' + error + '</pre>';
                    }
                }
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Root endpoint error: {e}")
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>❌ System Error</h1>
            <p>Error: {str(e)}</p>
            <p>Check logs for details.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        logger.info("Health check called")
        supabase = get_supabase_client()
        response = supabase.table('inventario_estilos').select('id').limit(1).execute()
        return {"status": "healthy", "database": "connected", "records": len(response.data)}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.get("/api/estilos", response_model=List[EstiloResponse])
async def get_estilos(search: Optional[str] = None):
    """Get estilos with prioridad=1"""
    try:
        logger.info(f"Getting estilos, search: {search}")
        supabase = get_supabase_client()
        
        query = supabase.table('inventario_estilos').select('id, nombre').eq('prioridad', 1).order('nombre')
        response = query.execute()
        estilos = response.data
        
        logger.info(f"Found {len(estilos)} estilos")
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            estilos = [
                estilo for estilo in estilos 
                if search_lower in estilo['nombre'].lower() or search in str(estilo['id'])
            ]
        
        # Convert IDs to strings
        for estilo in estilos:
            estilo['id'] = str(estilo['id'])
        
        return estilos
    except Exception as e:
        logger.error(f"Error fetching estilos: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching estilos: {str(e)}")

@app.get("/api/colores/{estilo_id}")
async def get_colores(estilo_id: Union[str, int], search: Optional[str] = None):
    """Get colors for an estilo"""
    try:
        logger.info(f"Getting colors for estilo: {estilo_id}, search: {search}")
        supabase = get_supabase_client()
        
        # Get inventory items
        inventario_query = supabase.table('inventario1').select('color_id, terex1').eq('estilo_id', estilo_id).gt('terex1', 0)
        inventario_response = inventario_query.execute()
        
        if not inventario_response.data:
            return []
        
        # Get unique color_ids and calculate stats
        color_stats = {}
        for item in inventario_response.data:
            color_id = str(item['color_id'])
            terex1 = item['terex1'] or 0
            
            if color_id not in color_stats:
                color_stats[color_id] = {'count': 1, 'terex1_total': terex1}
            else:
                color_stats[color_id]['count'] += 1
                color_stats[color_id]['terex1_total'] += terex1
        
        # Get color details
        color_ids = list(color_stats.keys())
        if not color_ids:
            return []
            
        colors_query = supabase.table('inventario_colores').select('id, color').in_('id', color_ids)
        colors_response = colors_query.execute()
        
        # Build response
        colors_list = []
        for color in colors_response.data:
            color_id = str(color['id'])
            if color_id in color_stats:
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
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            colors_list = [
                color for color in colors_list 
                if search_lower in color['color'].lower() or search in str(color['id'])
            ]
        
        logger.info(f"Found {len(colors_list)} colors")
        return colors_list
        
    except Exception as e:
        logger.error(f"Error fetching colors: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching colors: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")