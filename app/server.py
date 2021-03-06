import aiohttp
import asyncio
import uvicorn
from fastai import *
from fastai.vision import *
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, JSONResponse
from starlette.staticfiles import StaticFiles

export_file_url = 'https://drive.google.com/uc?export=download&id=1Iu7fjdlGSZAAKa_ckaZLGiA8qqtMYdQ_'
export_file_name = 'export.pkl'

classes = ['batman', 'captain america', 'deadpool', 'hulk', 'iron man', 'spiderman', 'superman', 'wolverine', 'wonder woman']
path = Path(__file__).parent

app = Starlette()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['X-Requested-With', 'Content-Type'])
app.mount('/static', StaticFiles(directory='app/static'))


async def download_file(url, dest):
    if dest.exists(): return
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.read()
            with open(dest, 'wb') as f:
                f.write(data)


async def setup_learner():
    await download_file(export_file_url, path / export_file_name)
    try:
        learn = load_learner(path, export_file_name)
        return learn
    except RuntimeError as e:
        if len(e.args) > 0 and 'CPU-only machine' in e.args[0]:
            print(e)
            message = "\n\nThis model was trained with an old version of fastai and will not work in a CPU environment.\n\nPlease update the fastai library in your training environment and export your model again.\n\nSee instructions for 'Returning to work' at https://course.fast.ai."
            raise RuntimeError(message)
        else:
            raise


loop = asyncio.get_event_loop()
tasks = [asyncio.ensure_future(setup_learner())]
learn = loop.run_until_complete(asyncio.gather(*tasks))[0]
loop.close()


@app.route('/')
async def homepage(request):
    html_file = path / 'view' / 'index.html'
    return HTMLResponse(html_file.open().read())


@app.route('/analyze', methods=['POST'])
async def analyze(request):
    img_data = await request.form()
    img_bytes = await (img_data['file'].read())
    img = open_image(BytesIO(img_bytes))
    
    pred_class, pred_idx, outputs = learn.predict(img)
    
    categories = learn.data.classes
    probabilities = [float(outputs[i]) for i in range(len(categories))]
    fig, ax = plt.subplots(figsize=(10,5))
    ax.barh(categories, probabilities, color='#7052CB', alpha=0.5)
    ax.invert_yaxis()
    ax.set_xlabel('probability')
    tmpfile = BytesIO()
    fig.savefig(tmpfile, format='png')
    encoded = base64.b64encode(tmpfile.getvalue()).decode("utf-8")
    image = '<img src=\'data:image/png;base64,{}\'>'.format(encoded)
    
    return JSONResponse({'result' : str(pred_class), 'plot' : image})


if __name__ == '__main__':
    if 'serve' in sys.argv:
        uvicorn.run(app=app, host='0.0.0.0', port=5000, log_level="info")
