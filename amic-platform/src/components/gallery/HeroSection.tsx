import { cn } from "@/lib/cn";

export interface HeroSectionProps {
  title: string;
  subtitle?: string;
  description?: string;
  backgroundUrl: string;
  height?: "sm" | "md" | "lg";
  className?: string;
}

const heightStyles = {
  sm: "min-h-[240px]",
  md: "min-h-[320px]",
  lg: "min-h-[400px]",
};

export function HeroSection({
  title,
  subtitle,
  description,
  backgroundUrl,
  height = "md",
  className,
}: HeroSectionProps) {
  const displaySubtitle = subtitle ?? description;
  return (
    <div
      className={cn(
        "relative flex items-center justify-center overflow-hidden rounded-corporate",
        heightStyles[height],
        className
      )}
    >
      <img
        src={backgroundUrl}
        alt=""
        className="absolute inset-0 w-full h-full object-cover"
        loading="lazy"
      />
      <div className="absolute inset-0 bg-amic/70" />
      <div className="relative z-10 text-center px-6">
        <h1 className="text-3xl md:text-4xl font-heading font-bold text-white tracking-tight">
          {title}
        </h1>
        {displaySubtitle && (
          <p className="mt-3 text-lg text-white/80 max-w-2xl mx-auto leading-relaxed">
            {displaySubtitle}
          </p>
        )}
      </div>
    </div>
  );
}
