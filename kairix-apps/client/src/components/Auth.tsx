import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setApiKey } from '@/lib/auth';

export function Auth() {
  const [key, setKey] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (key.trim()) {
      setApiKey(key.trim());
      navigate('/');
    }
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-background">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 px-6">
        <input
          type="password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="Enter access key"
          className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          autoFocus
        />
        <button
          type="submit"
          className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
        >
          Submit
        </button>
      </form>
    </div>
  );
}