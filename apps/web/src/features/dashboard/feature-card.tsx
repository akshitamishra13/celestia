import { Icon, type IconName } from "@/components/ui/icon";
import Link from "next/link";

type FeatureCardProps = {
  eyebrow: string;
  title: string;
  description: string;
  action: string;
  icon: IconName;
  tone: "sun" | "rose";
  href: string;
};

export function FeatureCard({ eyebrow, title, description, action, icon, tone, href }: FeatureCardProps) {
  return (
    <article className={`feature-card feature-card--${tone}`}>
      <div className="feature-card__top">
        <div className="feature-card__icon"><Icon name={icon} /></div>
        <span>{eyebrow}</span>
      </div>
      <div className="feature-card__body">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <Link className="feature-card__action" href={href}>
        {action}<Icon name="arrow" />
      </Link>
      <div className="feature-card__orbit" aria-hidden="true" />
    </article>
  );
}
