import React from 'react';
import ReactDOM from 'react-dom/client';
import { MantineProvider } from '@mantine/core';
import '@mantine/core/styles.css';
import '@mantine/charts/styles.css';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-sans/600.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/600.css';
import { App } from './App';
import { HttpListingsApi } from './api';
import './styles.css';
import { theme } from './theme';

const api = new HttpListingsApi(window.fetch.bind(window), `${import.meta.env.BASE_URL}api`);
const configuredRecentDays = Number(import.meta.env.VITE_DISKTRACKER_RECENT_DAYS ?? 7);
const recentDays = Number.isFinite(configuredRecentDays) && configuredRecentDays > 0 ? configuredRecentDays : 7;
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><MantineProvider theme={theme}><App api={api} base={import.meta.env.BASE_URL} storage={window.localStorage} recentDays={recentDays} now={() => new Date()} nextId={() => crypto.randomUUID()} /></MantineProvider></React.StrictMode>,
);
