import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { IconContext } from '@phosphor-icons/react';
import { App } from './App';
import './styles/base.css';
import './styles/studio.css';
import './styles/report.css';
import './styles/typography.css';
import './styles/preview.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <IconContext.Provider value={{ weight: 'light', className: 'research-icon' }}>
      <App />
    </IconContext.Provider>
  </StrictMode>,
);
