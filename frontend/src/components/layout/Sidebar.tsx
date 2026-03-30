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
  BarChart3,
  X,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'

const adminNavItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/products', icon: Package, label: 'Products' },
  { to: '/avatars', icon: User, label: 'Avatars' },
  { to: '/voices', icon: Mic, label: 'Voices' },
  { to: '/video-studio', icon: Film, label: 'Video Studio' },
  { to: '/video-queue', icon: ListVideo, label: 'Video Queue' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

const userNavItems = [
  { to: '/training', icon: GraduationCap, label: 'Training' },
  { to: '/roleplay', icon: MessageSquare, label: 'Roleplay' },
  { to: '/agent', icon: Bot, label: 'Sahayak' },
]

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { isAdmin } = useAuthStore()

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
    }`

  const handleNavClick = () => {
    // Close sidebar on mobile when a link is clicked
    if (window.innerWidth < 768) {
      onClose()
    }
  }

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col transform transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="p-4 md:p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div>
            <h1 className="text-lg md:text-xl font-bold text-primary-700 dark:text-primary-400">GroMo AI Trainer</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">AI-Powered Training Platform</p>
          </div>
          <button
            onClick={onClose}
            className="md:hidden p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <nav className="flex-1 p-3 md:p-4 space-y-1 overflow-y-auto">
          {isAdmin && (
            <>
              <p className="px-3 py-1.5 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Admin</p>
              {adminNavItems.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.to === '/'} className={linkClass} onClick={handleNavClick}>
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </NavLink>
              ))}
              <div className="my-3 border-t border-gray-200 dark:border-gray-700" />
            </>
          )}
          <p className="px-3 py-1.5 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
            {isAdmin ? 'Partner Tools' : 'Menu'}
          </p>
          {userNavItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={linkClass} onClick={handleNavClick}>
              <item.icon className="w-5 h-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-400 dark:text-gray-500 text-center">v1.0.0</p>
        </div>
      </aside>
    </>
  )
}
