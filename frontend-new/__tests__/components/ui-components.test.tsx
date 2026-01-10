import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import {
    AlertDialog,
    AlertDialogTrigger,
    AlertDialogContent,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogAction,
    AlertDialogCancel,
} from '@/components/ui/alert-dialog';
import {
    DropdownMenu,
    DropdownMenuTrigger,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuCheckboxItem,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuShortcut,
    DropdownMenuSub,
    DropdownMenuSubTrigger,
    DropdownMenuSubContent,
} from '@/components/ui/dropdown-menu';
import {
    Form,
    FormField,
    FormItem,
    FormLabel,
    FormControl,
    FormDescription,
    FormMessage,
    useFormField,
} from '@/components/ui/form';
import { useForm } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import * as ScrollAreaPrimitive from '@radix-ui/react-scroll-area';
import {
    Select,
    SelectTrigger,
    SelectContent,
    SelectItem,
    SelectValue,
    SelectLabel,
    SelectGroup,
    SelectSeparator,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

describe('UI components', () => {
    it('renders alert variants', () => {
        render(
            <Alert variant="destructive">
                <AlertTitle>Warning</AlertTitle>
                <AlertDescription>Be careful</AlertDescription>
            </Alert>
        );

        expect(screen.getByText('Warning')).toBeInTheDocument();
        expect(screen.getByText('Be careful')).toBeInTheDocument();
    });

    it('renders alert dialog content', () => {
        render(
            <AlertDialog defaultOpen>
                <AlertDialogTrigger>Open</AlertDialogTrigger>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Confirm</AlertDialogTitle>
                        <AlertDialogDescription>Are you sure?</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction>Confirm</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        );

        expect(screen.getByRole('heading', { name: 'Confirm' })).toBeInTheDocument();
        expect(screen.getByText('Are you sure?')).toBeInTheDocument();
    });

    it('renders dropdown menu items and sub menus', async () => {
        const user = userEvent.setup();
        render(
            <DropdownMenu defaultOpen>
                <DropdownMenuTrigger>Menu</DropdownMenuTrigger>
                <DropdownMenuContent>
                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                    <DropdownMenuItem>Item 1</DropdownMenuItem>
                    <DropdownMenuCheckboxItem checked>Checked</DropdownMenuCheckboxItem>
                    <DropdownMenuRadioGroup value="a">
                        <DropdownMenuRadioItem value="a">Radio A</DropdownMenuRadioItem>
                    </DropdownMenuRadioGroup>
                    <DropdownMenuSeparator />
                    <DropdownMenuSub>
                        <DropdownMenuSubTrigger>More</DropdownMenuSubTrigger>
                        <DropdownMenuSubContent>
                            <DropdownMenuItem>Sub Item</DropdownMenuItem>
                        </DropdownMenuSubContent>
                    </DropdownMenuSub>
                    <DropdownMenuShortcut>⌘K</DropdownMenuShortcut>
                </DropdownMenuContent>
            </DropdownMenu>
        );

        expect(screen.getByText('Actions')).toBeInTheDocument();
        expect(screen.getByText('Item 1')).toBeInTheDocument();

        await user.click(screen.getByText('More'));
        expect(screen.getByText('Sub Item')).toBeInTheDocument();
    });

    it('renders scroll area content', () => {
        render(
            <ScrollArea style={{ height: 100 }}>
                <div>Scrollable</div>
            </ScrollArea>
        );

        expect(screen.getByText('Scrollable')).toBeInTheDocument();
    });

    it('renders horizontal scroll bar styles', async () => {
        render(
            <ScrollAreaPrimitive.Root type="always" style={{ height: 100, width: 100 }}>
                <ScrollAreaPrimitive.Viewport>
                    <div style={{ width: 200, height: 20 }} />
                </ScrollAreaPrimitive.Viewport>
                <ScrollBar orientation="horizontal" />
            </ScrollAreaPrimitive.Root>
        );

        await waitFor(() => {
            const horizontalScrollbar = document.querySelector('[data-orientation="horizontal"]') as HTMLElement | null;
            expect(horizontalScrollbar).toBeTruthy();
            expect(horizontalScrollbar?.className ?? '').toContain('flex-col');
        });
    });

    it('renders select options', () => {
        render(
            <Select defaultOpen>
                <SelectTrigger>
                    <SelectValue placeholder="Pick one" />
                </SelectTrigger>
                <SelectContent>
                    <SelectGroup>
                        <SelectLabel>Group</SelectLabel>
                        <SelectItem value="one">One</SelectItem>
                        <SelectSeparator />
                    </SelectGroup>
                </SelectContent>
            </Select>
        );

        expect(screen.getByText('One')).toBeInTheDocument();
        expect(document.querySelector('.bg-border')).toBeInTheDocument();
    });

    it('renders textarea', () => {
        render(<Textarea placeholder="Type here" />);
        expect(screen.getByPlaceholderText('Type here')).toBeInTheDocument();
    });

    it('renders tooltip content', () => {
        render(
            <TooltipProvider>
                <Tooltip defaultOpen>
                    <TooltipTrigger asChild>
                        <button>Hover</button>
                    </TooltipTrigger>
                    <TooltipContent>Tooltip content</TooltipContent>
                </Tooltip>
            </TooltipProvider>
        );

        expect(screen.getAllByText('Tooltip content').length).toBeGreaterThan(0);
    });

    it('renders dropdown menu inset variants', () => {
        render(
            <DropdownMenu defaultOpen>
                <DropdownMenuTrigger>Menu</DropdownMenuTrigger>
                <DropdownMenuContent>
                    <DropdownMenuLabel inset>Inset Label</DropdownMenuLabel>
                    <DropdownMenuItem inset>Inset Item</DropdownMenuItem>
                    <DropdownMenuSub>
                        <DropdownMenuSubTrigger inset>Inset Sub</DropdownMenuSubTrigger>
                        <DropdownMenuSubContent>
                            <DropdownMenuItem>Sub Item</DropdownMenuItem>
                        </DropdownMenuSubContent>
                    </DropdownMenuSub>
                </DropdownMenuContent>
            </DropdownMenu>
        );

        expect(screen.getByText('Inset Label').className).toContain('pl-8');
        expect(screen.getByText('Inset Item').className).toContain('pl-8');
        expect(screen.getByText('Inset Sub').className).toContain('pl-8');
    });
});

describe('Form components', () => {
    it('throws when useFormField is used outside FormField', () => {
        const BadForm = () => {
            useFormField();
            return null;
        };
        const Wrapper = () => {
            const form = useForm<{ name: string }>({ defaultValues: { name: '' } });
            return (
                <Form {...form}>
                    <BadForm />
                </Form>
            );
        };

        expect(() => render(<Wrapper />)).toThrow('useFormField should be used within <FormField>');
    });

    it('renders form description and message', () => {
        const TestForm = () => {
            const form = useForm<{ name: string }>({
                defaultValues: { name: '' },
                mode: 'onChange',
            });

            return (
                <Form {...form}>
                    <form>
                        <FormField
                            control={form.control}
                            name="name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Name</FormLabel>
                                    <FormControl>
                                        <Input {...field} />
                                    </FormControl>
                                    <FormDescription>Help text</FormDescription>
                                    <FormMessage>Message</FormMessage>
                                </FormItem>
                            )}
                        />
                    </form>
                </Form>
            );
        };

        render(<TestForm />);

        expect(screen.getByText('Help text')).toBeInTheDocument();
        expect(screen.getByText('Message')).toBeInTheDocument();
    });
});
