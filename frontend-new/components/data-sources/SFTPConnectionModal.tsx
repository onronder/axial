import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Server, Loader2, Eye, EyeOff } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { useDataSources } from "@/hooks/useDataSources";
import { useToast } from "@/hooks/use-toast";

const sftpSchema = z.object({
  host: z.string().min(1, "Host is required"),
  port: z.number().min(1).max(65535, "Port must be between 1 and 65535"),
  username: z.string().min(1, "Username is required"),
  privateKey: z.string().min(1, "Private key is required"),
  passphrase: z.string().optional(),
});

type SFTPFormData = z.infer<typeof sftpSchema>;

interface SFTPConnectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function SFTPConnectionModal({
  open,
  onOpenChange,
  onSuccess,
}: SFTPConnectionModalProps) {
  const { connect } = useDataSources();
  const { toast } = useToast();
  const [isConnecting, setIsConnecting] = useState(false);
  const [showPassphrase, setShowPassphrase] = useState(false);

  const form = useForm<SFTPFormData>({
    resolver: zodResolver(sftpSchema),
    defaultValues: {
      host: "",
      port: 22,
      username: "",
      privateKey: "",
      passphrase: "",
    },
  });

  const onSubmit = async (data: SFTPFormData) => {
    setIsConnecting(true);
    try {
      await connect("sftp");
      // Mock using credentials
      console.log("Connecting to", `${data.username}@${data.host}:${data.port}`);
      toast({
        title: "SFTP connected",
        description: `Successfully connected to ${data.host}`,
      });
      form.reset();
      onOpenChange(false);
      onSuccess?.();
    } catch {
      toast({
        title: "Connection failed",
        description: "Unable to connect to SFTP server. Please check your credentials.",
        variant: "destructive",
      });
    } finally {
      setIsConnecting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-axio-gradient shadow-brand">
              <Server className="h-5 w-5 text-white" />
            </div>
            <div>
              <DialogTitle>Connect to SFTP</DialogTitle>
              <DialogDescription>
                Enter your SFTP server credentials
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <FormField
                control={form.control}
                name="host"
                render={({ field }) => (
                  <FormItem className="col-span-2">
                    <FormLabel>Host</FormLabel>
                    <FormControl>
                      <Input placeholder="sftp.example.com" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="port"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Port</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Username</FormLabel>
                  <FormControl>
                    <Input placeholder="your-username" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="privateKey"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Private Key</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;...&#10;-----END RSA PRIVATE KEY-----"
                      className="font-mono text-xs h-32 resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Paste your SSH private key (PEM format)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="passphrase"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Passphrase (optional)</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showPassphrase ? "text" : "password"}
                        placeholder="Key passphrase"
                        {...field}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full px-3"
                        onClick={() => setShowPassphrase(!showPassphrase)}
                      >
                        {showPassphrase ? (
                          <EyeOff className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <Eye className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isConnecting}
              >
                Cancel
              </Button>
              <Button type="submit" variant="gradient" disabled={isConnecting}>
                {isConnecting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Connect
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}