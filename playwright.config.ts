import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'.',testMatch:'desk.spec.ts',workers:1,use:{baseURL:'http://127.0.0.1:8765',headless:true},webServer:{command:'python3 server.py',url:'http://127.0.0.1:8765/api/health',reuseExistingServer:false,env:{ROLEPROOF_DB:'/tmp/roleproof-e2e.sqlite3'}},reporter:[['list']]});
