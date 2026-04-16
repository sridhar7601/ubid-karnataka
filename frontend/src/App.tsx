import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  GitMerge,
  Users,
  Fingerprint,
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import ResolutionDashboard from './pages/ResolutionDashboard';
import EntityProfile from './pages/EntityProfile';
import UnifiedEntities from './pages/UnifiedEntities';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/records', label: 'Records', icon: Database },
  { to: '/resolution', label: 'Entity Resolution', icon: GitMerge },
  { to: '/entities', label: 'Unified Entities', icon: Users },
];

function NavBar() {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2 shrink-0">
            <div className="bg-teal-600 text-white p-1.5 rounded-lg">
              <Fingerprint size={22} />
            </div>
            <span className="text-xl font-bold tracking-tight text-gray-900">
              UBID <span className="text-teal-600">Platform</span>
            </span>
          </NavLink>

          {/* Nav links */}
          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-teal-50 text-teal-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`
                }
              >
                <Icon size={16} />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 text-gray-900">
        <NavBar />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/records" element={<Dashboard />} />
            <Route path="/resolution" element={<ResolutionDashboard />} />
            <Route path="/entities" element={<UnifiedEntities />} />
            <Route path="/entity/:ubid" element={<EntityProfile />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
