import type { ReactNode } from "react";

type HeaderProps = {
  title: string;
  subtitle?: string;
  right?: ReactNode;
};

function Header({ title, subtitle, right }: HeaderProps) {
  return (
    <header className="app-header" role="banner">
      <div className="app-header__text">
        <h1 className="app-header__title">{title}</h1>
        {subtitle ? <p className="app-header__subtitle">{subtitle}</p> : null}
      </div>
      {right ? <div className="app-header__right">{right}</div> : null}
    </header>
  );
}

export default Header;
