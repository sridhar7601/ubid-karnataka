import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  GitMerge,
  Users,
  Fingerprint,
  Wand2,
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import ResolutionDashboard from './pages/ResolutionDashboard';
import EntityProfile from './pages/EntityProfile';
import UnifiedEntities from './pages/UnifiedEntities';
import Insights from './pages/Insights';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/resolution', label: 'Entity Resolution', icon: GitMerge },
  { to: '/entities', label: 'Unified Entities', icon: Users },
  { to: '/insights', label: 'Smart Query', icon: Wand2 },
];

function NavBar() {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2 shrink-0">
            <div className="bg-gradient-to-br from-teal-500 to-cyan-600 text-white p-1.5 rounded-lg shadow-sm shadow-teal-500/30">
              <Fingerprint size={22} />
            </div>
            <div>
              <div className="text-base font-bold tracking-tight text-gray-900 leading-tight">
                UBID Platform
              </div>
              <div className="text-[10px] uppercase tracking-wider text-gray-500">
                Karnataka Commerce & Industries
              </div>
            </div>
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
                      ? 'bg-teal-500 text-white shadow-sm'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`
                }
              >
                <Icon size={16} />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Live status pill */}
          <div className="hidden lg:flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            <span className="text-xs font-medium text-emerald-700">Live</span>
          </div>
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
            <Route path="/resolution" element={<ResolutionDashboard />} />
            <Route path="/entities" element={<UnifiedEntities />} />
            <Route path="/entity/:ubid" element={<EntityProfile />} />
            <Route path="/insights" element={<Insights />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
