import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import App from './App.jsx';
import './index.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ConfigProvider
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            colorPrimary: '#2d5016',
            colorBgBase: '#faf8f5',
            colorBgContainer: '#ffffff',
            colorBorder: 'rgba(90, 90, 90, 0.12)',
            borderRadius: 12,
            fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',
          },
        }}
      >
        <App />
      </ConfigProvider>
    </BrowserRouter>
  </StrictMode>
);
