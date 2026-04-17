import { Link, usePage } from '@inertiajs/react'
import React from 'react'
import {
  NavigationMenu,
  NavigationMenuList,
  NavigationMenuItem,
  NavigationMenuLink,
} from '@/components/ui/navigation-menu'

const navLinks = [
  { href: '/', label: 'Rating Calculator' },
  { href: '/chart-database/', label: 'Chart Database' },
  { href: '/databaseUpload/', label: 'Database Upload' },
]

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const { url } = usePage()

  const isActive = (href: string) =>
    href === '/' ? url === '/' : url.startsWith(href)

  return (
    <div className="min-h-screen bg-transparent">
      <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-xl border-b border-border shadow-sm">
        <div className="flex flex-wrap h-16 items-center justify-between px-6 max-w-screen-2xl mx-auto gap-2">
          <div className="flex items-center gap-2.5">
            <img src="/static/image/webLogo.png" alt="AstroDX" className="h-6 sm:h-7 object-contain" />
            <span className="text-border text-lg leading-none">·</span>
            <span className="text-primary font-semibold text-sm">maimai</span>
          </div>
          <NavigationMenu>
            <NavigationMenuList>
              {navLinks.map(({ href, label }) => (
                <NavigationMenuItem key={href}>
                  <NavigationMenuLink
                    render={<Link href={href} />}
                    data-active={isActive(href) ? '' : undefined}
                  >
                    {label}
                  </NavigationMenuLink>
                </NavigationMenuItem>
              ))}
            </NavigationMenuList>
          </NavigationMenu>
        </div>
      </header>
      <main>{children}</main>
    </div>
  )
}
