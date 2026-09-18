import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <Card className="w-full max-w-sm shadow-sm transition-shadow duration-200">
      <CardHeader className="text-center">
        <p className="text-sm font-medium tracking-tight">UAP</p>
        <CardTitle className="text-balance text-xl">{title}</CardTitle>
        <CardDescription className="text-pretty">{subtitle}</CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
      <CardFooter className="justify-center text-sm text-muted-foreground">
        {footer}
      </CardFooter>
    </Card>
  );
}
