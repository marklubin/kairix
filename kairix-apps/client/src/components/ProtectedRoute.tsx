import { hasApiKey } from '@/lib/auth';
import { PirateShip } from './PirateShip';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  // Show pirate ship if no API key
  if (!hasApiKey()) {
    return <PirateShip />;
  }

  return <>{children}</>;
}
