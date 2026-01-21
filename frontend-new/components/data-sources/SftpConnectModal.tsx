"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";

interface SftpConnectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConnected?: () => void;
}

export function SftpConnectModal({ open, onOpenChange, onConnected }: SftpConnectModalProps) {
  const { toast } = useToast();
  const [host, setHost] = useState("");
  const [port, setPort] = useState("22");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [privateKey, setPrivateKey] = useState("");
  const [rootPath, setRootPath] = useState("/");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const resetForm = () => {
    setHost("");
    setPort("22");
    setUsername("");
    setPassword("");
    setPrivateKey("");
    setRootPath("/");
    setError(null);
  };

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) {
      resetForm();
    }
    onOpenChange(nextOpen);
  };

  const handleSubmit = async () => {
    setError(null);
    if (!host.trim() || !username.trim()) {
      setError("Host and username are required.");
      return;
    }
    if (!password && !privateKey) {
      setError("Provide either a password or a private key.");
      return;
    }

    const parsedPort = Number(port);
    if (!Number.isInteger(parsedPort) || parsedPort < 1 || parsedPort > 65535) {
      setError("Port must be a valid integer between 1 and 65535.");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/integrations/sftp/connect", {
        host: host.trim(),
        port: parsedPort,
        username: username.trim(),
        password: password || null,
        private_key: privateKey || null,
        root_path: rootPath.trim() || "/",
      });

      toast({
        title: "SFTP connected",
        description: "Connection verified and saved.",
      });
      onConnected?.();
      handleClose(false);
    } catch (err) {
      const message =
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
        "Failed to connect to SFTP. Please verify the details.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>Connect SFTP</DialogTitle>
          <DialogDescription>
            Securely connect your SFTP server. Use a password or a private key.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }} className="grid gap-4">
          <div className="grid gap-2">
            <label className="text-sm font-medium text-foreground">Host</label>
            <Input value={host} onChange={(e) => setHost(e.target.value)} placeholder="sftp.example.com" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-2">
              <label className="text-sm font-medium text-foreground">Port</label>
              <Input value={port} onChange={(e) => setPort(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium text-foreground">Username</label>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-foreground">Password (optional)</label>
            <Input
              value={password}
              type="password"
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-foreground">Private Key (optional, PEM)</label>
            <Textarea
              value={privateKey}
              onChange={(e) => setPrivateKey(e.target.value)}
              rows={5}
              placeholder="-----BEGIN PRIVATE KEY-----"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-foreground">Root Path</label>
            <Input
              value={rootPath}
              onChange={(e) => setRootPath(e.target.value)}
              placeholder="/"
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => handleClose(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Connecting..." : "Connect"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
