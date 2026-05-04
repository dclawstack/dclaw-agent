"use client";

import { useEffect, useState } from "react";
import { listMarketplace } from "@/lib/api";

type MarketplaceItem = {
  id: string;
  name: string;
  description?: string;
  owner_name: string;
  install_count: number;
};

export default function MarketplacePage() {
  const [items, setItems] = useState<MarketplaceItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listMarketplace()
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Marketplace</h1>
      {loading ? (
        <p>Loading...</p>
      ) : items.length === 0 ? (
        <p className="text-gray-500">No public agents yet.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {items.map((item) => (
            <div
              key={item.id}
              className="p-4 bg-white rounded-lg border border-gray-100 shadow-sm"
            >
              <h2 className="font-semibold">{item.name}</h2>
              <p className="text-sm text-gray-500 mb-2">{item.description}</p>
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>{item.owner_name}</span>
                <span>{item.install_count} installs</span>
              </div>
              <button className="mt-3 w-full px-3 py-1.5 text-sm bg-brand text-white rounded hover:opacity-90">
                Install
              </button>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
