from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI()
TRANSCRIPTS_DIR = "transcripts"

@app.get("/transcript/{guild_id}/{channel_id}", response_class=HTMLResponse)
async def get_transcript(guild_id: str, channel_id: str):
    html_path = os.path.join(TRANSCRIPTS_DIR, guild_id, f"{channel_id}.html")
    if not os.path.exists(html_path):
        return HTMLResponse("<h2>Transcript not found</h2>", status_code=404)

    html_content = open(html_path, "r", encoding="utf-8").read()

    download_script = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <button onclick="downloadPDF()">Download PDF</button>
    <script>
    function downloadPDF(){
        html2canvas(document.body).then(canvas=>{
            const imgData = canvas.toDataURL('image/png');
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF('p','px',[canvas.width,canvas.height]);
            pdf.addImage(imgData,'PNG',0,0,canvas.width,canvas.height);
            pdf.save("transcript.pdf");
        })
    }
    </script>
    """
    return HTMLResponse(html_content + download_script)

