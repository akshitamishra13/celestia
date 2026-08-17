import { Icon, type IconName } from "@/components/ui/icon";

type FeatureCardProps = {
  eyebrow: string;
  title: string;
  description: string;
  action: string;
  icon: IconName;
  tone: "sun" | "rose";
};

export function FeatureCard({ eyebrow, title, description, action, icon, tone }: FeatureCardProps) {
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
      <a className="feature-card__action" href="#">
        {action}<Icon name="arrow" />
      </a>
      <div className="feature-card__orbit" aria-hidden="true" />
    </article>
  );
}
