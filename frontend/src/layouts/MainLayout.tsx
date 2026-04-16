import { Link } from '@inertiajs/react'
import React from 'react'
import {
  NavigationMenu,
  NavigationMenuList,
  NavigationMenuItem,
  NavigationMenuLink,
} from '@/components/ui/navigation-menu'

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <header className="border-b bg-background">
        <div className="flex h-14 items-center px-6">
          <NavigationMenu>
            <NavigationMenuList>
              <NavigationMenuItem>
                <NavigationMenuLink render={<Link href="/" />}>
                  Rating Calculator
                </NavigationMenuLink>
              </NavigationMenuItem>
              <NavigationMenuItem>
                <NavigationMenuLink render={<Link href="/chart-database/" />}>
                  Chart Database
                </NavigationMenuLink>
              </NavigationMenuItem>
              <NavigationMenuItem>
                <NavigationMenuLink render={<Link href="/databaseUpload/" />}>
                  Database Upload
                </NavigationMenuLink>
              </NavigationMenuItem>
            </NavigationMenuList>
          </NavigationMenu>
        </div>
      </header>
      {children}
    </div>
  )
}
