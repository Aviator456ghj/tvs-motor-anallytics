export default function Footer() {
  return (
    <footer className="mt-8 px-6 py-5 border-t border-card-border flex flex-col sm:flex-row items-center justify-between gap-2 text-[12px] text-muted-light">
      <span>CommerceOS © 2025. All rights reserved.</span>
      <div className="flex items-center gap-4">
        <a href="#" className="hover:text-muted">Privacy Policy</a>
        <a href="#" className="hover:text-muted">Terms of Service</a>
        <a href="#" className="hover:text-muted">Help Center</a>
      </div>
    </footer>
  );
}
