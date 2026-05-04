import Link from "next/link";

export default function Home() {
  return (
    <main className="p-8 max-w-5xl mx-auto">
      <h1 className="text-4xl font-bold text-brand mb-4">DClaw Agent</h1>
      <p className="text-lg text-gray-600 mb-8">
        Build, share, and sell AI agents.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card href="/agents" title="My Agents" desc="View and manage your agents" />
        <Card href="/builder" title="Agent Builder" desc="Create agents on a visual canvas" />
        <Card href="/marketplace" title="Marketplace" desc="Discover public agents" />
        <Card href="/runs" title="Run History" desc="Review execution logs" />
      </div>
    </main>
  );
}

function Card({ href, title, desc }: { href: string; title: string; desc: string }) {
  return (
    <Link
      href={href}
      className="block p-6 bg-white rounded-xl shadow hover:shadow-md transition border border-gray-100"
    >
      <h2 className="text-xl font-semibold mb-1">{title}</h2>
      <p className="text-gray-500">{desc}</p>
    </Link>
  );
}
