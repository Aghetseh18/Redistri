"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Server, Users, Package,
  ShoppingCart, Truck, GitMerge, Database,
} from "lucide-react";
import clsx from "clsx";

const nav = [
  { label: "Dashboard",   href: "/",              icon: LayoutDashboard },
  { label: "Cluster",     href: "/cluster",        icon: Server },
  { label: "Queries",     href: "/queries",        icon: GitMerge },
  { label: "─── CRUD ───", href: null,             icon: null },
  { label: "Clients",     href: "/crud/clients",   icon: Users },
  { label: "Articles",    href: "/crud/articles",  icon: Package },
  { label: "Commandes",   href: "/crud/commandes", icon: ShoppingCart },
  { label: "Livraisons",  href: "/crud/livraisons",icon: Truck },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-56 shrink-0 flex flex-col bg-gray-900 border-r border-gray-800 min-h-screen">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-gray-800">
        <Database className="text-blue-400" size={22} />
        <div>
          <p className="font-bold text-white text-sm leading-tight">Redis Cluster</p>
          <p className="text-gray-500 text-[10px]">Distributed DB Dashboard</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
        {nav.map((item, i) => {
          if (!item.href) {
            return (
              <p key={i} className="px-3 pt-3 pb-1 text-[10px] font-semibold text-gray-600 uppercase tracking-widest">
                {item.label}
              </p>
            );
          }
          const Icon = item.icon!;
          const active = path === item.href || (item.href !== "/" && path.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"
              )}
            >
              <Icon size={16} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-800 text-[10px] text-gray-600">
        University project · Distributed DB
      </div>
    </aside>
  );
}
