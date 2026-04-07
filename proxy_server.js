const http = require('http');
const httpProxy = require('http-proxy');

const STREAMLIT_PORT = 8080;
const PROXY_PORT = 5000;

const proxy = httpProxy.createProxyServer({
  ws: true,
  changeOrigin: true,
  xfwd: true,
  preserveHeaderKeyCase: true
});

proxy.on('error', (err, req, res) => {
  console.error('Proxy error:', err.message);
  if (res && res.writeHead) {
    res.writeHead(503, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: false, error: 'Service unavailable' }));
  }
});

proxy.on('proxyReq', (proxyReq, req, res, options) => {
  proxyReq.setHeader('X-Forwarded-Host', req.headers.host);
  proxyReq.setHeader('X-Forwarded-Proto', 'https');
  if (req.headers.cookie) {
    proxyReq.setHeader('Cookie', req.headers.cookie);
  }
});

proxy.on('proxyReqWs', (proxyReq, req, socket, options, head) => {
  socket.setTimeout(0);
  socket.setNoDelay(true);
  socket.setKeepAlive(true, 0);
  
  proxyReq.setHeader('X-Forwarded-Host', req.headers.host);
  proxyReq.setHeader('X-Forwarded-Proto', 'https');
  if (req.headers.cookie) {
    proxyReq.setHeader('Cookie', req.headers.cookie);
  }
});

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', req.headers.origin || '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Xsrftoken');
  res.setHeader('Access-Control-Allow-Credentials', 'true');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  proxy.web(req, res, { target: `http://localhost:${STREAMLIT_PORT}` });
});

server.on('upgrade', (req, socket, head) => {
  socket.setTimeout(0);
  socket.setNoDelay(true);
  socket.setKeepAlive(true, 0);
  
  socket.on('error', (err) => {
    console.error('WebSocket socket error:', err.message);
    socket.destroy();
  });
  
  proxy.ws(req, socket, head, { 
    target: `http://localhost:${STREAMLIT_PORT}`,
    ws: true
  });
});

server.listen(PROXY_PORT, '0.0.0.0', () => {
  console.log(`🔀 Reverse Proxy running on port ${PROXY_PORT}`);
  console.log(`   → All routes to Streamlit (port ${STREAMLIT_PORT})`);
  console.log(`   → WebSocket connections forwarded to Streamlit`);
});
