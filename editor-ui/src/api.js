import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:5000/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const getBlogs = async () => {
    const response = await api.get('/blogs');
    return response.data.blogs;
};

export const getPosts = async (blogId) => {
    const response = await axios.get(`${API_BASE_URL}/posts/${blogId}`);
    return response.data;
};

export const searchAcrossBlogs = async (query) => {
    const response = await axios.get(`${API_BASE_URL}/search`, { params: { q: query } });
    return response.data;
};

export const savePost = async (blogId, { title, content, isDraft, editLink }) => {
    const response = await api.post(`/posts/${blogId}`, {
        title,
        content,
        is_draft: isDraft,
        edit_link: editLink || '',
    });
    return response.data;
};

export const uploadImage = async (file) => {
    const formData = new FormData();
    formData.append('image', file);
    const response = await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const optimizeAllPost = async ({ title, content }) => {
    const response = await api.post('/optimize_all', {
        title,
        content,
    });
    return response.data;
};

export const improvePost = async ({ title, content, instructionType, customPrompt }) => {
    const response = await api.post('/improve', {
        title,
        content,
        instruction_type: instructionType || 'monetize',
        custom_prompt: customPrompt || '',
    });
    return response.data;
};

export const runToolAffiliate = async ({ title, content }) => {
    const response = await api.post('/tools/affiliate', {
        title,
        content,
    });
    return response.data;
};

export const runToolFactCheck = async ({ title, content }) => {
    const response = await api.post('/tools/factcheck', {
        title,
        content,
    });
    return response.data;
};

export const generateThumbnail = async ({ title, content }) => {
    const response = await api.post('/tools/thumbnail', {
        title,
        content,
    });
    return response.data;
};

export default api;
