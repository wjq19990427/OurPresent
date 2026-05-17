from fastapi import FastAPI

app = FastAPI(title="OurPresent API", version="0.1.0")


@app.get("/healthz")
async def health():
    return {"status": "ok"}
