import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Package,
  User,
  Mic,
  Film,
  ListVideo,
  GraduationCap,
  MessageSquare,
  Bot,
  Settings,
} from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/products', icon: Package, label: 'Products' },
  { to: '/avatars', icon: User, label: 'Avatars' },
  { to: '/voices', icon: Mic, label: 'Voices' },
  { to: '/video-studio', icon: Film, label: 'Video Studio' },
  { to: '/video-queue', icon: ListVideo, label: 'Video Queue' },
  { to: '/training', icon: GraduationCap, label: 'Training' },
  { to: '/roleplay', icon: MessageSquare, label: 'Roleplay' },
  { to: '/agent', icon: Bot, label: 'Sahayak' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h1 className="text-xl font-bold text-primary-700 dark:text-primary-400">GroMo AI Trainer</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">AI-Powered Training Platform</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-400 dark:text-gray-500 text-center">v1.0.0</p>
      </div>
    </aside>
  )
}
