import axios, { AxiosInstance } from 'axios';
import type {
  AuthResponse,
  User,
  SocialAccount,
  Post,
  DashboardStats,
  AnalyticsData,
  Subscription,
  Invoice,
  ApiKey,
  TeamMember,
} from '@/types';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8200',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle auth errors
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async login(email: string, password: string): Promise<AuthResponse> {
    const { data } = await this.client.post('/auth/login', { email, password });
    return data;
  }

  async signup(email: string, password: string, name: string): Promise<AuthResponse> {
    const { data } = await this.client.post('/auth/signup', { email, password, name });
    return data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
  }

  async getMe(): Promise<User> {
    const { data } = await this.client.get('/auth/me');
    return data;
  }

  // Social Accounts
  async getSocialAccounts(): Promise<SocialAccount[]> {
    const { data } = await this.client.get('/accounts');
    return data;
  }

  async connectAccount(platform: string): Promise<{ authUrl: string }> {
    const { data } = await this.client.post(`/accounts/connect/${platform}`);
    return data;
  }

  async disconnectAccount(accountId: string): Promise<void> {
    await this.client.delete(`/accounts/${accountId}`);
  }

  // Posts
  async getPosts(params?: { status?: string; limit?: number }): Promise<Post[]> {
    const { data } = await this.client.get('/posts', { params });
    return data;
  }

  async getPost(postId: string): Promise<Post> {
    const { data } = await this.client.get(`/posts/${postId}`);
    return data;
  }

  async createPost(post: {
    content: string;
    platforms: string[];
    scheduledAt?: string;
    mediaUrls?: string[];
  }): Promise<Post> {
    const { data } = await this.client.post('/posts', post);
    return data;
  }

  async updatePost(postId: string, updates: Partial<Post>): Promise<Post> {
    const { data } = await this.client.patch(`/posts/${postId}`, updates);
    return data;
  }

  async deletePost(postId: string): Promise<void> {
    await this.client.delete(`/posts/${postId}`);
  }

  async uploadMedia(file: File): Promise<{ url: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await this.client.post('/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  }

  // Dashboard
  async getDashboardStats(): Promise<DashboardStats> {
    const { data } = await this.client.get('/dashboard/stats');
    return data;
  }

  // Analytics
  async getAnalytics(params: {
    startDate: string;
    endDate: string;
    platform?: string;
  }): Promise<AnalyticsData[]> {
    const { data } = await this.client.get('/analytics', { params });
    return data;
  }

  // Billing
  async getSubscription(): Promise<Subscription> {
    const { data } = await this.client.get('/billing/subscription');
    return data;
  }

  async updateSubscription(planId: string): Promise<Subscription> {
    const { data } = await this.client.post('/billing/subscription', { planId });
    return data;
  }

  async getInvoices(): Promise<Invoice[]> {
    const { data } = await this.client.get('/billing/invoices');
    return data;
  }

  // API Keys
  async getApiKeys(): Promise<ApiKey[]> {
    const { data } = await this.client.get('/api-keys');
    return data;
  }

  async createApiKey(name: string): Promise<ApiKey> {
    const { data } = await this.client.post('/api-keys', { name });
    return data;
  }

  async revokeApiKey(keyId: string): Promise<void> {
    await this.client.delete(`/api-keys/${keyId}`);
  }

  // Team
  async getTeamMembers(): Promise<TeamMember[]> {
    const { data } = await this.client.get('/team');
    return data;
  }

  async inviteTeamMember(email: string, role: string): Promise<TeamMember> {
    const { data } = await this.client.post('/team/invite', { email, role });
    return data;
  }

  async removeTeamMember(memberId: string): Promise<void> {
    await this.client.delete(`/team/${memberId}`);
  }

  // Settings
  async updateProfile(updates: Partial<User>): Promise<User> {
    const { data } = await this.client.patch('/settings/profile', updates);
    return data;
  }
}

export const api = new ApiClient();
