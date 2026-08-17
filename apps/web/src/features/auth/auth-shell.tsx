"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/icon";
import { useAuth } from "./auth-provider";

type AuthMode = "login" | "signup";

export function AuthShell({ mode }: { mode: AuthMode }) {
  const { login, signup } = useAuth();
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name") ?? "");
    const email = String(data.get("email") ?? "");
    const password = String(data.get("password") ?? "");
    const confirmation = String(data.get("confirmation") ?? "");

    if (mode === "signup" && password !== confirmation) {
      setError("Passwords do not match.");
      setSubmitting(false);
      return;
    }

    try {
      if (mode === "login") await login(email, password);
      else await signup(name, email, password);
      router.replace("/dashboard");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to continue. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const isLogin = mode === "login";

  return (
    <main className="auth-page">
      <section className="auth-story">
        <Link className="auth-brand" href="/"><span><Icon name="sparkles" /></span>AstroLive</Link>
        <div className="auth-story__copy">
          <span className="section-kicker"><Icon name="sparkles" /> A thoughtful cosmic guide</span>
          <h1>Clarity for the journey within.</h1>
          <p>Explore your Vedic chart and relationships through a calm, constructive, and deeply personal experience.</p>
        </div>
        <div className="auth-cosmos" aria-hidden="true"><span /><span /><span /><span /></div>
        <p className="auth-quote">“The stars offer perspective. Your choices shape the path.”</p>
      </section>

      <section className="auth-form-panel">
        <div className="auth-form-wrap">
          <div className="auth-mobile-brand"><span><Icon name="sparkles" /></span>AstroLive</div>
          <span className="auth-eyebrow">{isLogin ? "Welcome back" : "Begin your journey"}</span>
          <h2>{isLogin ? "Sign in to your space" : "Create your account"}</h2>
          <p>{isLogin ? "Your chart and reports are waiting for you." : "Create a private space for your charts and reports."}</p>

          <form className="auth-form" onSubmit={handleSubmit}>
            {!isLogin && <label>Full name<input name="name" type="text" autoComplete="name" minLength={2} placeholder="Your full name" required /></label>}
            <label>Email address<input name="email" type="email" autoComplete="email" placeholder="you@example.com" required /></label>
            <label>Password<div className="password-field"><input name="password" type={showPassword ? "text" : "password"} autoComplete={isLogin ? "current-password" : "new-password"} minLength={isLogin ? 1 : 8} placeholder={isLogin ? "Enter your password" : "At least 8 characters"} required /><button type="button" onClick={() => setShowPassword((visible) => !visible)}>{showPassword ? "Hide" : "Show"}</button></div></label>
            {!isLogin && <label>Confirm password<input name="confirmation" type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={8} placeholder="Enter it once more" required /></label>}
            {error && <div className="auth-error" role="alert">{error}</div>}
            <button className="auth-submit" type="submit" disabled={submitting}>{submitting ? "Please wait…" : isLogin ? "Sign in" : "Create account"}<Icon name="arrow" /></button>
          </form>

          <p className="auth-switch">{isLogin ? "New to AstroLive?" : "Already have an account?"} <Link href={isLogin ? "/signup" : "/login"}>{isLogin ? "Create an account" : "Sign in"}</Link></p>
        </div>
      </section>
    </main>
  );
}
