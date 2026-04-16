'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, X, Calendar, Clock } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { api } from '@/lib/api';
import type { SocialAccount } from '@/types';

export default function NewPostPage() {
  const router = useRouter();
  const [content, setContent] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [scheduledAt, setScheduledAt] = useState('');
  const [mediaFiles, setMediaFiles] = useState<File[]>([]);
  const [mediaUrls, setMediaUrls] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const data = await api.getSocialAccounts();
      setAccounts(data.filter(a => a.isConnected));
    } catch (error) {
      console.error('Failed to fetch accounts:', error);
    }
  };

  const handlePlatformToggle = (platform: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(platform)
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    );
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    setIsUploading(true);
    try {
      const uploadPromises = files.map(file => api.uploadMedia(file));
      const results = await Promise.all(uploadPromises);
      const urls = results.map(r => r.url);
      
      setMediaFiles(prev => [...prev, ...files]);
      setMediaUrls(prev => [...prev, ...urls]);
    } catch (error) {
      console.error('Failed to upload media:', error);
      alert('Failed to upload media files');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveMedia = (index: number) => {
    setMediaFiles(prev => prev.filter((_, i) => i !== index));
    setMediaUrls(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (status: 'draft' | 'scheduled' | 'published') => {
    if (!content.trim()) {
      alert('Please enter post content');
      return;
    }

    if (selectedPlatforms.length === 0) {
      alert('Please select at least one platform');
      return;
    }

    if (status === 'scheduled' && !scheduledAt) {
      alert('Please select a schedule time');
      return;
    }

    setIsLoading(true);
    try {
      await api.createPost({
        content,
        platforms: selectedPlatforms,
        scheduledAt: status === 'scheduled' ? scheduledAt : undefined,
        mediaUrls: mediaUrls.length > 0 ? mediaUrls : undefined,
      });

      router.push('/dashboard/posts');
    } catch (error) {
      console.error('Failed to create post:', error);
      alert('Failed to create post');
    } finally {
      setIsLoading(false);
    }
  };

  const characterCount = content.length;
  const maxCharacters = 280;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Create Post</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Compose and schedule your social media post
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Post Content</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="What's on your mind?"
                  rows={8}
                  className="resize-none"
                />
                <div className="flex items-center justify-between mt-2">
                  <span className={`text-sm ${
                    characterCount > maxCharacters
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    {characterCount} / {maxCharacters} characters
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Media
                </label>
                <div className="space-y-3">
                  {mediaFiles.length > 0 && (
                    <div className="grid grid-cols-2 gap-3">
                      {mediaFiles.map((file, index) => (
                        <div key={index} className="relative group">
                          <img
                            src={URL.createObjectURL(file)}
                            alt={`Upload ${index + 1}`}
                            className="w-full h-32 object-cover rounded-lg"
                          />
                          <button
                            onClick={() => handleRemoveMedia(index)}
                            className="absolute top-2 right-2 p-1 bg-red-600 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <label className="flex items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-blue-500 dark:hover:border-blue-500 transition-colors">
                    <div className="text-center">
                      <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {isUploading ? 'Uploading...' : 'Click to upload media'}
                      </span>
                    </div>
                    <input
                      type="file"
                      multiple
                      accept="image/*,video/*"
                      onChange={handleFileChange}
                      className="hidden"
                      disabled={isUploading}
                    />
                  </label>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Platforms</CardTitle>
            </CardHeader>
            <CardContent>
              {accounts.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                    No accounts connected
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push('/dashboard/accounts')}
                  >
                    Connect Account
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  {accounts.map((account) => (
                    <label
                      key={account.id}
                      className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={selectedPlatforms.includes(account.platform)}
                        onChange={() => handlePlatformToggle(account.platform)}
                        className="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 capitalize">
                          {account.platform}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          @{account.username}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Schedule</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                label="Schedule for"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Leave empty to publish immediately
              </p>
            </CardContent>
          </Card>

          <div className="space-y-3">
            <Button
              onClick={() => handleSubmit('published')}
              className="w-full"
              isLoading={isLoading}
              disabled={accounts.length === 0}
            >
              Publish Now
            </Button>
            <Button
              onClick={() => handleSubmit('scheduled')}
              variant="secondary"
              className="w-full"
              isLoading={isLoading}
              disabled={accounts.length === 0 || !scheduledAt}
            >
              <Clock className="w-4 h-4 mr-2" />
              Schedule Post
            </Button>
            <Button
              onClick={() => handleSubmit('draft')}
              variant="outline"
              className="w-full"
              isLoading={isLoading}
            >
              Save as Draft
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
