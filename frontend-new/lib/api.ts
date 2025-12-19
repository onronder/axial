import axios from 'axios';

export const api = axios.create({
    baseURL: '/api/py',
    headers: {
        'Content-Type': 'application/json',
    },
});

export const authFetch = api;
