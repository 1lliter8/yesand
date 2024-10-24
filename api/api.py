from ninja import NinjaAPI

api = NinjaAPI(
    title='YesAnd API',
    description='API for YesAnd project',
    version='1.0.0',
    docs_url='/docs',
)


@api.get('/hello')
def hello(request):
    return {'message': 'Hello from yes& API'}
