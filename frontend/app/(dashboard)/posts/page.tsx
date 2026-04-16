'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileText, Plus, Filter } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { api } from '@/lib/api';
import type { Post } from '@/types';
import { formatDateTime, formatNumber } from '@/lib/utils';

export default function PostsPage() {
  const router = useRouter();
  const [posts, setPosts] = useState<Post[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    fetchPosts();
  }, [statusFilter]);

  const fetchPosts = async () => {
    try {
      const params = statusFilter !== 'all' ? { status: statusFilter } : {};
      const data = await api.getPosts(params);
      setPosts(data);
    } catch (error) {
      console.error('Failed to fetch posts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (postId: string) => {
    if (!confirm('Are you sure you want to delete this post?')) return;

    try {
      await api.deletePost(postId);
      fetchPosts();
    } catch (error) {
      console.error('Failed to delete post:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Posts</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage your social media posts
          </p>
        </div>
        <Button onClick={() => router.push('/dashboard/posts/new')}>
          <Plus className="w-4 h-4 mr-2" />
          Create Post
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={[
            { value: 'all', label: 'All Posts' },
            { value: 'draft', label: 'Drafts' },
            { value: 'scheduled', label: 'Scheduled' },
            { value: 'published', label: 'Published' },
            { value: 'failed', label: 'Failed' },
          ]}
        />
      </div>

      {posts.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              No posts yet
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Create your first post to get started
            </p>
            <Button onClick={() => router.push('/dashboard/posts/new')}>
              <Plus className="w-4 h-4 mr-2" />
              Create Post
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <Card key={post.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                        post.status === 'published'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : post.status === 'scheduled'
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                          : post.status === 'failed'
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                          : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400'
                      }`}>
                        {post.status}
                      </span>
                      <div className="flex items-center gap-2">
                        {post.platforms.map((platform) => (
                          <span
                            key={platform}
                            className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded capitalize"
                          >
                            {platform}
                          </span>
                        ))}
                      </div>
                    </div>

                    <p className="text-gray-900 dark:text-gray-100 mb-3 whitespace-pre-wrap">
                      {post.content}
                    </p>

                    {post.mediaUrls && post.mediaUrls.length > 0 && (
                      <div className="flex gap-2 mb-3">
                        {post.mediaUrls.slice(0, 3).map((url, index) => (
                          <img
                            key={index}
                            src={url}
                            alt={`Media ${index + 1}`}
                            className="w-20 h-20 object-cover rounded"
                          />
                        ))}
                        {post.mediaUrls.length > 3 && (
                          <div className="w-20 h-20 bg-gray-100 dark:bg-gray-700 rounded flex items-center justify-center text-sm text-gray-600 dark:text-gray-400">
                            +{post.mediaUrls.length - 3}
                          </div>
                        )}
                      </div>
                    )}

                    <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                      {post.scheduledAt && (
                        <span>Scheduled: {formatDateTime(post.scheduledAt)}</span>
                      )}
                      {post.publishedAt && (
                        <span>Published: {formatDateTime(post.publishedAt)}</span>
                      )}
                      {!post.scheduledAt && !post.publishedAt && (
                        <span>Created: {formatDateTime(post.createdAt)}</span>
                      )}
                    </div>
                  </div>

                  <div className="ml-6 flex flex-col items-end gap-3">
                    {post.analytics && (
                      <div className="text-right">
                        <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          {formatNumber(post.analytics.views)}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">views</p>
                        <div className="flex items-center gap-3 mt-2 text-xs text-gray-600 dark:text-gray-400">
                          <span>{formatNumber(post.analytics.likes)} likes</span>
                          <span>{formatNumber(post.analytics.comments)} comments</span>
                        </div>
                      </div>
                    )}

                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => router.push(`/dashboard/posts/${post.id}`)}
                      >
                        View
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(post.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
