import { useState } from 'react';

import reactLogo from './assets/react.svg';
import './App.css';
import { useAppStore } from './store/appStore';

function App() {
  const [count, setCount] = useState(0);
  const appTitle = useAppStore((state) => state.appTitle);

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank" rel="noreferrer">
          <img src="/vite.svg" className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank" rel="noreferrer">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>{appTitle}</h1>
      <div className="card">
        <button onClick={() => setCount((current) => current + 1)}>count is {count}</button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">Enter passenger details to see if they survive the voyage.</p>
    </>
  );
}

export default App;
