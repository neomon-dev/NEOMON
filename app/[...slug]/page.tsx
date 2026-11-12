import Link from "next/link";

type PlaceholderPageProps = {
  params: Promise<{ slug: string[] }>;
};

export default async function PlaceholderPage({ params }: PlaceholderPageProps) {
  const { slug } = await params;
  const title = slug.map((segment) => segment.replace(/-/g, " ")).join(" / ");

  return (
    <main className="placeholder-page">
      <p className="eyebrow blue">FOUNDATION SCOPE</p>
      <h1>{title}</h1>
      <p>This workspace is reserved for the next NEOMON milestone. No research data is being fabricated.</p>
      <Link className="outline-button" href="/">Return to dashboard <span>→</span></Link>
    </main>
  );
}
