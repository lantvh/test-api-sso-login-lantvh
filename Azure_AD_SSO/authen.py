from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from msal import ConfidentialClientApplication
import uuid
# from fastapi_sessions import SessionMiddleware
from starlette.middleware.sessions import SessionMiddleware
import datetime
import msgraph
import httpx
from fastapi.responses import RedirectResponse
import requests

app = FastAPI()

# Thông tin của ứng dụng Azure AD App Registration
CLIENT_ID = 'dc405df2-286b-4965-8cca-d835f103e48b'
CLIENT_SECRET = '8acd651d-c965-44da-b954-de802bdbef18'
AUTHORITY = 'https://login.microsoftonline.com/c5ec5abe-76c1-46cb-b3fe-c3b0071ffdb3'
# CLIENT_SECRET_VALUE = 'e788Q~oJ0LSW~UB.hEIremrXJYM4j3prnMwMKcyP'

# Thêm middleware để lưu trữ thông tin phiên với secret key tuỳ ý
app.add_middleware(SessionMiddleware, secret_key='12345678')

# API tạo một trang HTML đơn giản với nút Sign In
@app.get('/')
async def index(request: Request):
    html_content = """
    <html>
        <body>
            <form action="/signin" method="post">
                <input type="submit" value="Sign In">
            </form>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# API đăng nhập qua Micorsoft SSO
@app.post('/signin')
async def signin(request: Request):
    # Tạo một session_id ngẫu nhiên để sử dụng khi lưu trữ trạng thái phiên
    session_id = str(uuid.uuid4())

    # Tạo một phiên MSAL
    cca = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY
    )

    # Tạo URL xác thực và lưu trữ session_id
    auth_url = cca.get_authorization_request_url(
        scopes=['User.Read'],
        state=session_id,
        redirect_uri='http://localhost:8000/callback'
    )
    request.session[session_id] = {}

    # Chuyển hướng đến URL xác thực
    response = Response(status_code=302)
    response.headers['Location'] = auth_url
    # return RedirectResponse(auth_url)
    return response

# API trả về kết quả đăng nhập và thông tin người dùng
@app.get('/callback')
async def callback(request: Request):
    # Lấy mã truy cập từ URL callback
    code = request.query_params.get('code')
    # Lấy session_id từ state parameter trong URL callback
    state = request.query_params.get('state')
    # Tạo một phiên MSAL
    cca = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET_VALUE,
        authority=AUTHORITY
    )

    # Lấy thông tin phiên
    session = request.session.get(state)

    # Xác thực mã truy cập và lưu trữ mã thông báo truy cập vào session
    result = cca.acquire_token_by_authorization_code(
        code=code,
        redirect_uri='http://localhost:8000/callback',
        scopes=['User.Read']
    )

    # Xử lý lỗi xác thực
    if 'error' in result:
        error_message = result.get('error_description', 'Unknown error')
        return HTMLResponse(content=f'<html><body><h1>Sign In Failed: {error_message}</h1></body></html>',
                            status_code=200)

    # Lưu phiên đăng nhập với access token
    access_token = result.get('access_token')

    # Gọi API Microsoft Graph để lấy thông tin người dùng
    headers = {'Authorization': f'Bearer {access_token}'}
    graph_response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
    if graph_response.status_code == 200:
        user_info = graph_response.json()
        user_name = user_info.get('displayName')
        user_email = user_info.get('mail')
        html_content = f"""
            <html>
                <body>
                    <h1>Signed In Successful</h1>
                    <p>Name: {user_name}</p>
                    <p>Email: {user_email}</p>
                    <p>Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </body>
            </html>
        """
        return HTMLResponse(content=html_content, status_code=200)
    else:
        error_message = graph_response.json().get('error', {}).get('message', 'Unknown error')
        return HTMLResponse(content=f'<html><body><h1>Sign In Failed: {error_message}</h1></body></html>',
                            status_code=200)


