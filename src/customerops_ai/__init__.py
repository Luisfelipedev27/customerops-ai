def main() -> None:
    import uvicorn

    uvicorn.run("customerops_ai.api:app", host="127.0.0.1", port=8000)
