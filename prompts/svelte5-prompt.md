Version 5 comes with an overhauled syntax and reactivity system. While it may look different at first, you’ll soon notice many similarities. This guide goes over the changes in detail and shows you how to upgrade. Along with it, we also provide information on _why_ we did these changes.

You don’t have to migrate to the new syntax right away - Svelte 5 still supports the old Svelte 4 syntax, and you can mix and match components using the new syntax with components using the old and vice versa. We expect many people to be able to upgrade with only a few lines of code changed initially. There’s also a [migration script](#Migration-script) that helps you with many of these steps automatically.

Reactivity syntax changes[](#Reactivity-syntax-changes)
-------------------------------------------------------

At the heart of Svelte 5 is the new runes API. Runes are basically compiler instructions that inform Svelte about reactivity. Syntactically, runes are functions starting with a dollar-sign.

### let -> $state[](#Reactivity-syntax-changes-let-$state)

In Svelte 4, a `let` declaration at the top level of a component was implicitly reactive. In Svelte 5, things are more explicit: a variable is reactive when created using the `$state` rune. Let’s migrate the counter to runes mode by wrapping the counter in `$state`:

    <script>
    	let count = $state(0);
    </script>

Nothing else changes. `count` is still the number itself, and you read and write directly to it, without a wrapper like `.value` or `getCount()`.

> Why we did this
>
> `let` being implicitly reactive at the top level worked great, but it meant that reactivity was constrained - a `let` declaration anywhere else was not reactive. This forced you to resort to using stores when refactoring code out of the top level of components for reuse. This meant you had to learn an entirely separate reactivity model, and the result often wasn’t as nice to work with. Because reactivity is more explicit in Svelte 5, you can keep using the same API outside the top level of components. Head to [the tutorial](/tutorial) to learn more.

### $: -> $derived/$effect[](#Reactivity-syntax-changes-$:-$derived-$effect)

In Svelte 4, a `$:` statement at the top level of a component could be used to declare a derivation, i.e. state that is entirely defined through a computation of other state. In Svelte 5, this is achieved using the `$derived` rune:

    <script>
    	let count = $state(0);
    	$: const double = $derived(count * 2);
    </script>

As with `$state`, nothing else changes. `double` is still the number itself, and you read it directly, without a wrapper like `.value` or `getDouble()`.

A `$:` statement could also be used to create side effects. In Svelte 5, this is achieved using the `$effect` rune:

    <script>
    	let count = $state(0);
    	$:$effect(() => {
    		if (count > 5) {
    			alert('Count is too high!');
    		}
    	});
    </script>

> Why we did this
>
> `$:` was a great shorthand and easy to get started with: you could slap a `$:` in front of most code and it would somehow work. This intuitiveness was also its drawback the more complicated your code became, because it wasn’t as easy to reason about. Was the intent of the code to create a derivation, or a side effect? With `$derived` and `$effect`, you have a bit more up-front decision making to do (spoiler alert: 90% of the time you want `$derived`), but future-you and other developers on your team will have an easier time.
>
> There were also gotchas that were hard to spot:
>
> *   `$:` only updated directly before rendering, which meant you could read stale values in-between rerenders
> *   `$:` only ran once per tick, which meant that statements may run less often than you think
> *   `$:` dependencies were determined through static analysis of the dependencies. This worked in most cases, but could break in subtle ways during a refactoring where dependencies would be for example moved into a function and no longer be visible as a result
> *   `$:` statements were also ordered by using static analysis of the dependencies. In some cases there could be ties and the ordering would be wrong as a result, needing manual interventions. Ordering could also break while refactoring code and some dependencies no longer being visible as a result.
>
> Lastly, it wasn’t TypeScript-friendly (our editor tooling had to jump through some hoops to make it valid for TypeScript), which was a blocker for making Svelte’s reactivity model truly universal.
>
> `$derived` and `$effect` fix all of these by
>
> *   always returning the latest value
> *   running as often as needed to be stable
> *   determining the dependencies at runtime, and therefore being immune to refactorings
> *   executing dependencies as needed and therefore being immune to ordering problems
> *   being TypeScript-friendly

### export let -> $props[](#Reactivity-syntax-changes-export-let-$props)

In Svelte 4, properties of a component were declared using `export let`. Each property was one declaration. In Svelte 5, all properties are declared through the `$props` rune, through destructuring:

    <script>
    	export let optional = 'unset';
    	export let required;
    	let { optional = 'unset', required } = $props();
    </script>

There are multiple cases where declaring properties becomes less straightforward than having a few `export let` declarations:

*   you want to rename the property, for example because the name is a reserved identifier (e.g. `class`)
*   you don’t know which other properties to expect in advance
*   you want to forward every property to another component

All these cases need special syntax in Svelte 4:

*   renaming: `export { klass as class}`
*   other properties: `$$restProps`
*   all properties `$$props`

In Svelte 5, the `$props` rune makes this straightforward without any additional Svelte-specific syntax:

*   renaming: use property renaming `let { class: klass } = $props();`
*   other properties: use spreading `let { foo, bar, ...rest } = $props();`
*   all properties: don’t destructure `let props = $props();`

    <script>
    	let klass = '';
    	export { klass as class};
    	let { class: klass, ...rest } = $props();
    </script>
    <button class={klass} {...$$restPropsrest}>click me</button>

> Why we did this
>
> `export let` was one of the more controversial API decisions, and there was a lot of debate about whether you should think about a property being `export`ed or `import`ed. `$props` doesn’t have this trait. It’s also in line with the other runes, and the general thinking reduces to “everything special to reactivity in Svelte is a rune”.
>
> There were also a lot of limitations around `export let`, which required additional API, as shown above. `$props` unite this in one syntactical concept that leans heavily on regular JavaScript destructuring syntax.

Event changes[](#Event-changes)
-------------------------------

Event handlers have been given a facelift in Svelte 5. Whereas in Svelte 4 we use the `on:` directive to attach an event listener to an element, in Svelte 5 they are properties like any other (in other words - remove the colon):

    <script>
    	let count = $state(0);
    </script>

    <button on:click={() => count++}>
    	clicks: {count}
    </button>

Since they’re just properties, you can use the normal shorthand syntax...

    <script>
    	let count = $state(0);

    	function onclick() {
    		count++;
    	}
    </script>

    <button {onclick}>
    	clicks: {count}
    </button>

...though when using a named event handler function it’s usually better to use a more descriptive name.

### Component events[](#Event-changes-Component-events)

In Svelte 4, components could emit events by creating a dispatcher with `createEventDispatcher`.

This function is deprecated in Svelte 5. Instead, components should accept _callback props_ - which means you then pass functions as properties to these components:

App

    <script>
    	import Pump from './Pump.svelte';

    	let size = $state(15);
    	let burst = $state(false);

    	function reset() {
    		size = 15;
    		burst = false;
    	}
    </script>

    <Pump
    	on:inflate={(power) => {
    		size += power.detail;
    		if (size > 75) burst = true;
    	}}
    	on:deflate={(power) => {
    		if (size > 0) size -= power.detail;
    	}}
    />

    {#if burst}
    	<button onclick={reset}>new balloon</button>
    	<span class="boom">💥</span>
    {:else}
    	<span class="balloon" style="scale: {0.01 * size}">
    		🎈
    	</span>
    {/if}

    <script lang="ts">
    	import Pump from './Pump.svelte';

    	let size = $state(15);
    	let burst = $state(false);

    	function reset() {
    		size = 15;
    		burst = false;
    	}
    </script>

    <Pump
    	on:inflate={(power) => {
    		size += power.detail;
    		if (size > 75) burst = true;
    	}}
    	on:deflate={(power) => {
    		if (size > 0) size -= power.detail;
    	}}
    />

    {#if burst}
    	<button onclick={reset}>new balloon</button>
    	<span class="boom">💥</span>
    {:else}
    	<span class="balloon" style="scale: {0.01 * size}">
    		🎈
    	</span>
    {/if}

Pump

    <script>
    	import { createEventDispatcher } from 'svelte';
    	const dispatch = createEventDispatcher();

    	let { inflate, deflate } = $props();
    	let power = $state(5);
    </script>

    <button onclick={() => dispatch('inflate', power)inflate(power)}>
    	inflate
    </button>
    <button onclick={() => dispatch('deflate', power)deflate(power)}>
    	deflate
    </button>
    <button onclick={() => power--}>-</button>
    Pump power: {power}
    <button onclick={() => power++}>+</button>

    <script lang="ts">
    	import { createEventDispatcher } from 'svelte';
    	const dispatch = createEventDispatcher();

    	let { inflate, deflate } = $props();
    	let power = $state(5);
    </script>

    <button onclick={() => dispatch('inflate', power)inflate(power)}>
    	inflate
    </button>
    <button onclick={() => dispatch('deflate', power)deflate(power)}>
    	deflate
    </button>
    <button onclick={() => power--}>-</button>
    Pump power: {power}
    <button onclick={() => power++}>+</button>

### Bubbling events[](#Event-changes-Bubbling-events)

Instead of doing `<button on:click>` to ‘forward’ the event from the element to the component, the component should accept an `onclick` callback prop:

    <script>
    	let { onclick } = $props();
    </script>

    <button on:click {onclick}>
    	click me
    </button>

Note that this also means you can ‘spread’ event handlers onto the element along with other props instead of tediously forwarding each event separately:

    <script>
    	let props = $props();
    </script>

    <button {...$$props} on:click on:keydown on:all_the_other_stuff {...props}>
    	click me
    </button>

### Event modifiers[](#Event-changes-Event-modifiers)

In Svelte 4, you can add event modifiers to handlers:

    <button on:click|once|preventDefault={handler}>...</button>

Modifiers are specific to `on:` and as such do not work with modern event handlers. Adding things like `event.preventDefault()` inside the handler itself is preferable, since all the logic lives in one place rather than being split between handler and modifiers.

Since event handlers are just functions, you can create your own wrappers as necessary:

    <script>
    	function once(fn) {
    		return function (event) {
    			if (fn) fn.call(this, event);
    			fn = null;
    		};
    	}

    	function preventDefault(fn) {
    		return function (event) {
    			event.preventDefault();
    			fn.call(this, event);
    		};
    	}
    </script>

    <button onclick={once(preventDefault(handler))}>...</button>

There are three modifiers — `capture`, `passive` and `nonpassive` — that can’t be expressed as wrapper functions, since they need to be applied when the event handler is bound rather than when it runs.

For `capture`, we add the modifier to the event name:

    <button onclickcapture={...}>...</button>

Changing the [`passive`](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#using_passive_listeners) option of an event handler, meanwhile, is not something to be done lightly. If you have a use case for it — and you probably don’t! — then you will need to use an action to apply the event handler yourself.

### Multiple event handlers[](#Event-changes-Multiple-event-handlers)

In Svelte 4, this is possible:

    <button on:click={one} on:click={two}>...</button>

Duplicate attributes/properties on elements — which now includes event handlers — are not allowed. Instead, do this:

    <button
    	onclick={(e) => {
    		one(e);
    		two(e);
    	}}
    >
    	...
    </button>

When spreading props, local event handlers must go _after_ the spread, or they risk being overwritten:

    <button
    	{...props}
    	onclick={(e) => {
    		doStuff(e);
    		props.onclick?.(e);
    	}}
    >
    	...
    </button>

> Why we did this
>
> `createEventDispatcher` was always a bit boilerplate-y:
>
> *   import the function
> *   call the function to get a dispatch function
> *   call said dispatch function with a string and possibly a payload
> *   retrieve said payload on the other end through a `.detail` property, because the event itself was always a `CustomEvent`
>
> It was always possible to use component callback props, but because you had to listen to DOM events using `on:`, it made sense to use `createEventDispatcher` for component events due to syntactical consistency. Now that we have event attributes (`onclick`), it’s the other way around: Callback props are now the more sensible thing to do.
>
> The removal of event modifiers is arguably one of the changes that seems like a step back for those who’ve liked the shorthand syntax of event modifiers. Given that they are not used that frequently, we traded a smaller surface area for more explicitness. Modifiers also were inconsistent, because most of them were only useable on DOM elements.
>
> Multiple listeners for the same event are also no longer possible, but it was something of an anti-pattern anyway, since it impedes readability: if there are many attributes, it becomes harder to spot that there are two handlers unless they are right next to each other. It also implies that the two handlers are independent, when in fact something like `event.stopImmediatePropagation()` inside `one` would prevent `two` from being called.
>
> By deprecating `createEventDispatcher` and the `on:` directive in favour of callback props and normal element properties, we:
>
> *   reduce Svelte’s learning curve
> *   remove boilerplate, particularly around `createEventDispatcher`
> *   remove the overhead of creating `CustomEvent` objects for events that may not even have listeners
> *   add the ability to spread event handlers
> *   add the ability to know which event handlers were provided to a component
> *   add the ability to express whether a given event handler is required or optional
> *   increase type safety (previously, it was effectively impossible for Svelte to guarantee that a component didn’t emit a particular event)

Snippets instead of slots[](#Snippets-instead-of-slots)
-------------------------------------------------------

In Svelte 4, content can be passed to components using slots. Svelte 5 replaces them with snippets which are more powerful and flexible, and as such slots are deprecated in Svelte 5.

They continue to work, however, and you can pass snippets to a component that uses slots:

Child

    <slot />
    <hr />
    <slot name="foo" message="hello" />

Parent

    <script>
    	import Child from './Child.svelte';
    </script>

    <Child>
    	default child content

    	{#snippet foo({ message })}
    		message from child: {message}
    	{/snippet}
    </Child>

    <script lang="ts">
    	import Child from './Child.svelte';
    </script>

    <Child>
    	default child content

    	{#snippet foo({ message })}
    		message from child: {message}
    	{/snippet}
    </Child>

(The reverse is not true — you cannot pass slotted content to a component that uses [`{@render ...}`](/docs/svelte/@render) tags.)

When using custom elements, you should still use `<slot />` like before. In a future version, when Svelte removes its internal version of slots, it will leave those slots as-is, i.e. output a regular DOM tag instead of transforming it.

### Default content[](#Snippets-instead-of-slots-Default-content)

In Svelte 4, the easiest way to pass a piece of UI to the child was using a `<slot />`. In Svelte 5, this is done using the `children` prop instead, which is then shown with `{@render children()}`:

    <script>
    	let { children } = $props();
    </script>

    <slot />
    {@render children?.()}

### Multiple content placeholders[](#Snippets-instead-of-slots-Multiple-content-placeholders)

If you wanted multiple UI placeholders, you had to use named slots. In Svelte 5, use props instead, name them however you like and `{@render ...}` them:

    <script>
    	let { header, main, footer } = $props();
    </script>

    <header>
    	<slot name="header" />
    	{@render header()}
    </header>

    <main>
    	<slot name="main" />
    	{@render main()}
    </main>

    <footer>
    	<slot name="footer" />
    	{@render footer()}
    </footer>

### Passing data back up[](#Snippets-instead-of-slots-Passing-data-back-up)

In Svelte 4, you would pass data to a `<slot />` and then retrieve it with `let:` in the parent component. In Svelte 5, snippets take on that responsibility:

App

    <script>
    	import List from './List.svelte';
    </script>

    <List items={['one', 'two', 'three']} let:item>
    	{#snippet item(text)}
    		<span>{text}</span>
    	{/snippet}
    	<span slot="empty">No items yet</span>
    	{#snippet empty()}
    		<span>No items yet</span>
    	{/snippet}
    </List>

    <script lang="ts">
    	import List from './List.svelte';
    </script>

    <List items={['one', 'two', 'three']} let:item>
    	{#snippet item(text)}
    		<span>{text}</span>
    	{/snippet}
    	<span slot="empty">No items yet</span>
    	{#snippet empty()}
    		<span>No items yet</span>
    	{/snippet}
    </List>

List

    <script>
    	let { items, item, empty } = $props();
    </script>

    {#if items.length}
    	<ul>
    		{#each items as entry}
    			<li>
    				<slot item={entry} />
    				{@render item(entry)}
    			</li>
    		{/each}
    	</ul>
    {:else}
    	<slot name="empty" />
    	{@render empty?.()}
    {/if}

    <script lang="ts">
    	let { items, item, empty } = $props();
    </script>

    {#if items.length}
    	<ul>
    		{#each items as entry}
    			<li>
    				<slot item={entry} />
    				{@render item(entry)}
    			</li>
    		{/each}
    	</ul>
    {:else}
    	<slot name="empty" />
    	{@render empty?.()}
    {/if}

> Why we did this
>
> Slots were easy to get started with, but the more advanced the use case became, the more involved and confusing the syntax became:
>
> *   the `let:` syntax was confusing to many people as it _creates_ a variable whereas all other `:` directives _receive_ a variable
> *   the scope of a variable declared with `let:` wasn’t clear. In the example above, it may look like you can use the `item` slot prop in the `empty` slot, but that’s not true
> *   named slots had to be applied to an element using the `slot` attribute. Sometimes you didn’t want to create an element, so we had to add the `<svelte:fragment>` API
> *   named slots could also be applied to a component, which changed the semantics of where `let:` directives are available (even today us maintainers often don’t know which way around it works)
>
> Snippets solve all of these problems by being much more readable and clear. At the same time they’re more powerful as they allow you to define sections of UI that you can render _anywhere_, not just passing them as props to a component.

Migration script[](#Migration-script)
-------------------------------------

By now you should have a pretty good understanding of the before/after and how the old syntax relates to the new syntax. It probably also became clear that a lot of these migrations are rather technical and repetitive - something you don’t want to do by hand.

We thought the same, which is why we provide a migration script to do most of the migration automatically. You can upgrade your project by using `npx sv migrate svelte-5`. This will do the following things:

*   bump core dependencies in your `package.json`
*   migrate to runes (`let` -> `$state` etc)
*   migrate to event attributes for DOM elements (`on:click` -> `onclick`)
*   migrate slot creations to render tags (`<slot />` -> `{@render children()}`)
*   migrate slot usages to snippets (`<div slot="x">...</div>` -> `{#snippet x()}<div>...</div>{/snippet}`)
*   migrate obvious component creations (`new Component(...)` -> `mount(Component, ...)`)

You can also migrate a single component in VS Code through the `Migrate Component to Svelte 5 Syntax` command, or in our Playground through the `Migrate` button.

Not everything can be migrated automatically, and some migrations need manual cleanup afterwards. The following sections describe these in more detail.

### run[](#Migration-script-run)

You may see that the migration script converts some of your `$:` statements to a `run` function which is imported from `svelte/legacy`. This happens if the migration script couldn’t reliably migrate the statement to a `$derived` and concluded this is a side effect instead. In some cases this may be wrong and it’s best to change this to use a `$derived` instead. In other cases it may be right, but since `$:` statements also ran on the server but `$effect` does not, it isn’t safe to transform it as such. Instead, `run` is used as a stopgap solution. `run` mimics most of the characteristics of `$:`, in that it runs on the server once, and runs as `$effect.pre` on the client (`$effect.pre` runs _before_ changes are applied to the DOM; most likely you want to use `$effect` instead).

    <script>
    	import { run } from 'svelte/legacy';
    	run(() => {
    	$effect(() => {
    		// some side effect code
    	})
    </script>

### Event modifiers[](#Migration-script-Event-modifiers)

Event modifiers are not applicable to event attributes (e.g. you can’t do `onclick|preventDefault={...}`). Therefore, when migrating event directives to event attributes, we need a function-replacement for these modifiers. These are imported from `svelte/legacy`, and should be migrated away from in favor of e.g. just using `event.preventDefault()`.

    <script>
    	import { preventDefault } from 'svelte/legacy';
    </script>

    <button
    	onclick={preventDefault((event) => {
    		event.preventDefault();
    		// ...
    	})}
    >
    	click me
    </button>

### Things that are not automigrated[](#Migration-script-Things-that-are-not-automigrated)

The migration script does not convert `createEventDispatcher`. You need to adjust those parts manually. It doesn’t do it because it’s too risky because it could result in breakage for users of the component, which the migration script cannot find out.

The migration script does not convert `beforeUpdate/afterUpdate`. It doesn’t do it because it’s impossible to determine the actual intent of the code. As a rule of thumb you can often go with a combination of `$effect.pre` (runs at the same time as `beforeUpdate` did) and `tick` (imported from `svelte`, allows you to wait until changes are applied to the DOM and then do some work).

Components are no longer classes[](#Components-are-no-longer-classes)
---------------------------------------------------------------------

In Svelte 3 and 4, components are classes. In Svelte 5 they are functions and should be instantiated differently. If you need to manually instantiate components, you should use `mount` or `hydrate` (imported from `svelte`) instead. If you see this error using SvelteKit, try updating to the latest version of SvelteKit first, which adds support for Svelte 5. If you’re using Svelte without SvelteKit, you’ll likely have a `main.js` file (or similar) which you need to adjust:

    import { function mount<Props extends Record<string, any>, Exports extends Record<string, any>>(component: ComponentType<SvelteComponent<Props>> | Component<Props, Exports, any>, options: MountOptions<Props>): ExportsMounts a component to the given target and returns the exports and potentially the props (if compiled with accessors: true) of the component.
    Transitions will play during the initial render unless the intro option is set to false.
    mount } from 'svelte';
    import type App = SvelteComponent<Record<string, any>, any, any>
    const App: LegacyComponentTypeApp from './App.svelte'

    const app = new App({ target: document.getElementById("app") });
    const const app: {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<string, any>app = mount<Record<string, any>, {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<...>>(component: ComponentType<...> | Component<...>, options: MountOptions<...>): {
        ...;
    } & Record<...>Mounts a component to the given target and returns the exports and potentially the props (if compiled with accessors: true) of the component.
    Transitions will play during the initial render unless the intro option is set to false.
    mount(const App: LegacyComponentTypeApp, { target: Document | Element | ShadowRootTarget element where the component will be mounted.
    target: var document: DocumentMDN Reference
    document.Document.getElementById(elementId: string): HTMLElement | nullReturns a reference to the first object with the specified value of the ID attribute.
    @paramelementId String that specifies the ID value.getElementById("app") });

    export default const app: {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<string, any>app;

`mount` and `hydrate` have the exact same API. The difference is that `hydrate` will pick up the Svelte’s server-rendered HTML inside its target and hydrate it. Both return an object with the exports of the component and potentially property accessors (if compiled with `accessors: true`). They do not come with the `$on`, `$set` and `$destroy` methods you may know from the class component API. These are its replacements:

For `$on`, instead of listening to events, pass them via the `events` property on the options argument.

    import { function mount<Props extends Record<string, any>, Exports extends Record<string, any>>(component: ComponentType<SvelteComponent<Props>> | Component<Props, Exports, any>, options: MountOptions<Props>): ExportsMounts a component to the given target and returns the exports and potentially the props (if compiled with accessors: true) of the component.
    Transitions will play during the initial render unless the intro option is set to false.
    mount } from 'svelte';
    import type App = SvelteComponent<Record<string, any>, any, any>
    const App: LegacyComponentTypeApp from './App.svelte'

    const app = new App({ target: document.getElementById("app") });
    app.$on('event', callback);
    const const app: {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<string, any>app = mount<Record<string, any>, {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<...>>(component: ComponentType<...> | Component<...>, options: MountOptions<...>): {
        ...;
    } & Record<...>Mounts a component to the given target and returns the exports and potentially the props (if compiled with accessors: true) of the component.
    Transitions will play during the initial render unless the intro option is set to false.
    mount(const App: LegacyComponentTypeApp, { target: Document | Element | ShadowRootTarget element where the component will be mounted.
    target: var document: DocumentMDN Reference
    document.Document.getElementById(elementId: string): HTMLElement | nullReturns a reference to the first object with the specified value of the ID attribute.
    @paramelementId String that specifies the ID value.getElementById("app"), events?: Record<string, (e: any) => any> | undefinedAllows the specification of events.
    @deprecatedUse callback props instead.events: { event: anyevent: callback } });

> Note that using `events` is discouraged — instead, [use callbacks](#Event-changes)

For `$set`, use `$state` instead to create a reactive property object and manipulate it. If you’re doing this inside a `.js` or `.ts` file, adjust the ending to include `.svelte`, i.e. `.svelte.js` or `.svelte.ts`.

    import { function mount<Props extends Record<string, any>, Exports extends Record<string, any>>(component: ComponentType<SvelteComponent<Props>> | Component<Props, Exports, any>, options: MountOptions<Props>): ExportsMounts a component to the given target and returns the exports and potentially the props (if compiled with accessors: true) of the component.
    Transitions will play during the initial render unless the intro option is set to false.
    mount } from 'svelte';
    import type App = SvelteComponent<Record<string, any>, any, any>
    const App: LegacyComponentTypeApp from './App.svelte'

    const app = new App({ target: document.getElementById("app"), props: { foo: 'bar' } });
    app.$set({ foo: 'baz' });
    const const props: {
        foo: string;
    }props = function $state<{
        foo: string;
    }>(initial: {
        foo: string;
    }): {
        foo: string;
    } (+1 overload)
    namespace $stateDeclares reactive state.
    Example:
    let count = $state(0);https://svelte.dev/docs/svelte/$state
    @paraminitial The initial value$state({ foo: stringfoo: 'bar' });
    const const app: {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<string, any>app = mount<Record<string, any>, {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<...>>(component: ComponentType<...> | Component<...>, options: MountOptions<...>): {
        ...;
    } & Record<...>Mounts a component to the given target and returns the exports and potentially the props (if compiled with accessors: true) of the component.
    Transitions will play during the initial render unless the intro option is set to false.
    mount(const App: LegacyComponentTypeApp, { target: Document | Element | ShadowRootTarget element where the component will be mounted.
    target: var document: DocumentMDN Reference
    document.Document.getElementById(elementId: string): HTMLElement | nullReturns a reference to the first object with the specified value of the ID attribute.
    @paramelementId String that specifies the ID value.getElementById("app"), props?: Record<string, any> | undefinedComponent properties.
    props });
    const props: {
        foo: string;
    }props.foo: stringfoo = 'baz';

For `$destroy`, use `unmount` instead.

    import { function mount<Props extends Record<string, any>, Exports extends Record<string, any>>(component: ComponentType<SvelteComponent<Props>> | Component<Props, Exports, any>, options: MountOptions<Props>): ExportsMounts a component to the given target and returns the exports and potentially the props (if compiled with accessors: true) of the component.
    Transitions will play during the initial render unless the intro option is set to false.
    mount, function unmount(component: Record<string, any>, options?: {
        outro?: boolean;
    } | undefined): Promise<void>Unmounts a component that was previously mounted using mount or hydrate.
    Since 5.13.0, if options.outro is true, transitions will play before the component is removed from the DOM.
    Returns a Promise that resolves after transitions have completed if options.outro is true, or immediately otherwise (prior to 5.13.0, returns void).
    import { mount, unmount } from 'svelte';
    import App from './App.svelte';

    const app = mount(App, { target: document.body });

    // later...
    unmount(app, { outro: true });unmount } from 'svelte';
    import type App = SvelteComponent<Record<string, any>, any, any>
    const App: LegacyComponentTypeApp from './App.svelte'

    const app = new App({ target: document.getElementById("app"), props: { foo: 'bar' } });
    app.$destroy();
    const const app: {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<string, any>app = mount<Record<string, any>, {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<...>>(component: ComponentType<...> | Component<...>, options: MountOptions<...>): {
        ...;
    } & Record<...>Mounts a component to the given target and returns the exports and potentially the props (if compiled with accessors: true) of the component.
    Transitions will play during the initial render unless the intro option is set to false.
    mount(const App: LegacyComponentTypeApp, { target: Document | Element | ShadowRootTarget element where the component will be mounted.
    target: var document: DocumentMDN Reference
    document.Document.getElementById(elementId: string): HTMLElement | nullReturns a reference to the first object with the specified value of the ID attribute.
    @paramelementId String that specifies the ID value.getElementById("app") });
    function unmount(component: Record<string, any>, options?: {
        outro?: boolean;
    } | undefined): Promise<void>Unmounts a component that was previously mounted using mount or hydrate.
    Since 5.13.0, if options.outro is true, transitions will play before the component is removed from the DOM.
    Returns a Promise that resolves after transitions have completed if options.outro is true, or immediately otherwise (prior to 5.13.0, returns void).
    import { mount, unmount } from 'svelte';
    import App from './App.svelte';

    const app = mount(App, { target: document.body });

    // later...
    unmount(app, { outro: true });unmount(const app: {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<string, any>app);

As a stop-gap-solution, you can also use `createClassComponent` or `asClassComponent` (imported from `svelte/legacy`) instead to keep the same API known from Svelte 4 after instantiating.

    import { function createClassComponent<Props extends Record<string, any>, Exports extends Record<string, any>, Events extends Record<string, any>, Slots extends Record<string, any>>(options: ComponentConstructorOptions<Props> & {
        component: ComponentType<SvelteComponent<Props, Events, Slots>> | Component<Props>;
    }): SvelteComponent<Props, Events, Slots> & ExportsTakes the same options as a Svelte 4 component and the component function and returns a Svelte 4 compatible component.
    @deprecatedUse this only as a temporary solution to migrate your imperative component code to Svelte 5.createClassComponent } from 'svelte/legacy';
    import type App = SvelteComponent<Record<string, any>, any, any>
    const App: LegacyComponentTypeApp from './App.svelte'

    const app = new App({ target: document.getElementById("app") });
    const const app: SvelteComponent<Record<string, any>, any, any> & Record<string, any>app = createClassComponent<Record<string, any>, Record<string, any>, any, any>(options: ComponentConstructorOptions<Record<string, any>> & {
        component: Component<...> | ComponentType<...>;
    }): SvelteComponent<...> & Record<...>Takes the same options as a Svelte 4 component and the component function and returns a Svelte 4 compatible component.
    @deprecatedUse this only as a temporary solution to migrate your imperative component code to Svelte 5.createClassComponent({ component: Component<Record<string, any>, {}, string> | ComponentType<SvelteComponent<Record<string, any>, any, any>>component: const App: LegacyComponentTypeApp, ComponentConstructorOptions<Props extends Record<string, any> = Record<string, any>>.target: Document | Element | ShadowRoottarget: var document: DocumentMDN Reference
    document.Document.getElementById(elementId: string): HTMLElement | nullReturns a reference to the first object with the specified value of the ID attribute.
    @paramelementId String that specifies the ID value.getElementById("app") });

    export default const app: SvelteComponent<Record<string, any>, any, any> & Record<string, any>app;

If this component is not under your control, you can use the `compatibility.componentApi` compiler option for auto-applied backwards compatibility, which means code using `new Component(...)` keeps working without adjustments (note that this adds a bit of overhead to each component). This will also add `$set` and `$on` methods for all component instances you get through `bind:this`.

    /// svelte.config.js
    export default {
    	compilerOptions: {
        compatibility: {
            componentApi: number;
        };
    }compilerOptions: {
    		compatibility: {
        componentApi: number;
    }compatibility: {
    			componentApi: numbercomponentApi: 4
    		}
    	}
    };

Note that `mount` and `hydrate` are _not_ synchronous, so things like `onMount` won’t have been called by the time the function returns and the pending block of promises will not have been rendered yet (because `#await` waits a microtask to wait for a potentially immediately-resolved promise). If you need that guarantee, call `flushSync` (import from `'svelte'`) after calling `mount/hydrate`.

### Server API changes[](#Components-are-no-longer-classes-Server-API-changes)

Similarly, components no longer have a `render` method when compiled for server side rendering. Instead, pass the function to `render` from `svelte/server`:

    import { function render<Comp extends SvelteComponent<any> | Component<any>, Props extends ComponentProps<Comp> = ComponentProps<Comp>>(...args: {} extends Props ? [component: Comp extends SvelteComponent<any> ? ComponentType<Comp> : Comp, options?: {
        props?: Omit<Props, "$$slots" | "$$events">;
        context?: Map<any, any>;
    }] : [component: Comp extends SvelteComponent<any> ? ComponentType<Comp> : Comp, options: {
        props: Omit<Props, "$$slots" | "$$events">;
        context?: Map<any, any>;
    }]): RenderOutputOnly available on the server and when compiling with the server option.
    Takes a component and returns an object with body and head properties on it, which you can use to populate the HTML when server-rendering your app.
    render } from 'svelte/server';
    import type App = SvelteComponent<Record<string, any>, any, any>
    const App: LegacyComponentTypeApp from './App.svelte';

    const { html, head } = App.render({ props: { message: 'hello' }});
    const { const html: stringhtml, const head: stringHTML that goes into the &#x3C;head>
    head } = render<SvelteComponent<Record<string, any>, any, any>, Record<string, any>>(component: ComponentType<SvelteComponent<Record<string, any>, any, any>>, options?: {
        ...;
    } | undefined): RenderOutputOnly available on the server and when compiling with the server option.
    Takes a component and returns an object with body and head properties on it, which you can use to populate the HTML when server-rendering your app.
    render(const App: LegacyComponentTypeApp, { props?: Omit<Record<string, any>, "$$slots" | "$$events"> | undefinedprops: { message: stringmessage: 'hello' }});

In Svelte 4, rendering a component to a string also returned the CSS of all components. In Svelte 5, this is no longer the case by default because most of the time you’re using a tooling chain that takes care of it in other ways (like SvelteKit). If you need CSS to be returned from `render`, you can set the `css` compiler option to `'injected'` and it will add `<style>` elements to the `head`.

### Component typing changes[](#Components-are-no-longer-classes-Component-typing-changes)

The change from classes towards functions is also reflected in the typings: `SvelteComponent`, the base class from Svelte 4, is deprecated in favour of the new `Component` type which defines the function shape of a Svelte component. To manually define a component shape in a `d.ts` file:

    import type { interface Component<Props extends Record<string, any> = {}, Exports extends Record<string, any> = {}, Bindings extends keyof Props | "" = string>Can be used to create strongly typed Svelte components.
    Example:You have component library on npm called component-library, from which
    you export a component called MyComponent. For Svelte+TypeScript users,
    you want to provide typings. Therefore you create a index.d.ts:
    import type { Component } from 'svelte';
    export declare const MyComponent: Component&#x3C;{ foo: string }> {}Typing this makes it possible for IDEs like VS Code with the Svelte extension
    to provide intellisense and to use the component like this in a Svelte file
    with TypeScript:
    &#x3C;script lang="ts">
    	import { MyComponent } from "component-library";
    &#x3C;/script>
    &#x3C;MyComponent foo={'bar'} />Component } from 'svelte';
    export declare const const MyComponent: Component<{
        foo: string;
    }, {}, string>MyComponent: interface Component<Props extends Record<string, any> = {}, Exports extends Record<string, any> = {}, Bindings extends keyof Props | "" = string>Can be used to create strongly typed Svelte components.
    Example:You have component library on npm called component-library, from which
    you export a component called MyComponent. For Svelte+TypeScript users,
    you want to provide typings. Therefore you create a index.d.ts:
    import type { Component } from 'svelte';
    export declare const MyComponent: Component&#x3C;{ foo: string }> {}Typing this makes it possible for IDEs like VS Code with the Svelte extension
    to provide intellisense and to use the component like this in a Svelte file
    with TypeScript:
    &#x3C;script lang="ts">
    	import { MyComponent } from "component-library";
    &#x3C;/script>
    &#x3C;MyComponent foo={'bar'} />Component<{
    	foo: stringfoo: string;
    }>;

To declare that a component of a certain type is required:

    import { import ComponentAComponentA, import ComponentBComponentB } from 'component-library';
    import type { SvelteComponent } from 'svelte';
    import type { interface Component<Props extends Record<string, any> = {}, Exports extends Record<string, any> = {}, Bindings extends keyof Props | "" = string>Can be used to create strongly typed Svelte components.
    Example:You have component library on npm called component-library, from which
    you export a component called MyComponent. For Svelte+TypeScript users,
    you want to provide typings. Therefore you create a index.d.ts:
    import type { Component } from 'svelte';
    export declare const MyComponent: Component&#x3C;{ foo: string }> {}Typing this makes it possible for IDEs like VS Code with the Svelte extension
    to provide intellisense and to use the component like this in a Svelte file
    with TypeScript:
    &#x3C;script lang="ts">
    	import { MyComponent } from "component-library";
    &#x3C;/script>
    &#x3C;MyComponent foo={'bar'} />Component } from 'svelte';

    let C: typeof SvelteComponent<{ foo: string }> = $state(
    let let C: Component<{
        foo: string;
    }, {}, string>C: interface Component<Props extends Record<string, any> = {}, Exports extends Record<string, any> = {}, Bindings extends keyof Props | "" = string>Can be used to create strongly typed Svelte components.
    Example:You have component library on npm called component-library, from which
    you export a component called MyComponent. For Svelte+TypeScript users,
    you want to provide typings. Therefore you create a index.d.ts:
    import type { Component } from 'svelte';
    export declare const MyComponent: Component&#x3C;{ foo: string }> {}Typing this makes it possible for IDEs like VS Code with the Svelte extension
    to provide intellisense and to use the component like this in a Svelte file
    with TypeScript:
    &#x3C;script lang="ts">
    	import { MyComponent } from "component-library";
    &#x3C;/script>
    &#x3C;MyComponent foo={'bar'} />Component<{ foo: stringfoo: string }> = function $state<any>(initial: any): any (+1 overload)
    namespace $stateDeclares reactive state.
    Example:
    let count = $state(0);https://svelte.dev/docs/svelte/$state
    @paraminitial The initial value$state(
    	var Math: MathAn intrinsic object that provides basic mathematics functionality and constants.
    Math.Math.random(): numberReturns a pseudorandom number between 0 and 1.
    random() ? import ComponentAComponentA : import ComponentBComponentB
    );

The two utility types `ComponentEvents` and `ComponentType` are also deprecated. `ComponentEvents` is obsolete because events are defined as callback props now, and `ComponentType` is obsolete because the new `Component` type is the component type already (i.e. `ComponentType<SvelteComponent<{ prop: string }>>` is equivalent to `Component<{ prop: string }>`).

### bind:this changes[](#Components-are-no-longer-classes-bind:this-changes)

Because components are no longer classes, using `bind:this` no longer returns a class instance with `$set`, `$on` and `$destroy` methods on it. It only returns the instance exports (`export function/const`) and, if you’re using the `accessors` option, a getter/setter-pair for each property.

<svelte:component> is no longer necessary[](#svelte:component-is-no-longer-necessary)
-------------------------------------------------------------------------------------

In Svelte 4, components are _static_ — if you render `<Thing>`, and the value of `Thing` changes, [nothing happens](/playground/7f1fa24f0ab44c1089dcbb03568f8dfa?version=4.2.18). To make it dynamic you had to use `<svelte:component>`.

This is no longer true in Svelte 5:

    <script>
    	import A from './A.svelte';
    	import B from './B.svelte';

    	let Thing = $state();
    </script>

    <select bind:value={Thing}>
    	<option value={A}>A</option>
    	<option value={B}>B</option>
    </select>

    <!-- these are equivalent -->
    <Thing />
    <svelte:component this={Thing} />

While migrating, keep in mind that your component’s name should be capitalized (`Thing`) to distinguish it from elements, unless using dot notation.

### Dot notation indicates a component[](#svelte:component-is-no-longer-necessary-Dot-notation-indicates-a-component)

In Svelte 4, `<foo.bar>` would create an element with a tag name of `"foo.bar"`. In Svelte 5, `foo.bar` is treated as a component instead. This is particularly useful inside `each` blocks:

    {#each items as item}
    	<item.component {...item.props} />
    {/each}

Whitespace handling changed[](#Whitespace-handling-changed)
-----------------------------------------------------------

Previously, Svelte employed a very complicated algorithm to determine if whitespace should be kept or not. Svelte 5 simplifies this which makes it easier to reason about as a developer. The rules are:

*   Whitespace between nodes is collapsed to one whitespace
*   Whitespace at the start and end of a tag is removed completely
*   Certain exceptions apply such as keeping whitespace inside `pre` tags

As before, you can disable whitespace trimming by setting the `preserveWhitespace` option in your compiler settings or on a per-component basis in `<svelte:options>`.

Modern browser required[](#Modern-browser-required)
---------------------------------------------------

Svelte 5 requires a modern browser (in other words, not Internet Explorer) for various reasons:

*   it uses [`Proxies`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Proxy)
*   elements with `clientWidth` / `clientHeight`/`offsetWidth`/`offsetHeight` bindings use a [`ResizeObserver`](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver) rather than a convoluted `<iframe>` hack
*   `<input type="range" bind:value={...} />` only uses an `input` event listener, rather than also listening for `change` events as a fallback

The `legacy` compiler option, which generated bulkier but IE-friendly code, no longer exists.

Changes to compiler options[](#Changes-to-compiler-options)
-----------------------------------------------------------

*   The `false` / `true` (already deprecated previously) and the `"none"` values were removed as valid values from the `css` option
*   The `legacy` option was repurposed
*   The `hydratable` option has been removed. Svelte components are always hydratable now
*   The `enableSourcemap` option has been removed. Source maps are always generated now, tooling can choose to ignore it
*   The `tag` option was removed. Use `<svelte:options customElement="tag-name" />` inside the component instead
*   The `loopGuardTimeout`, `format`, `sveltePath`, `errorMode` and `varsReport` options were removed

The children prop is reserved[](#The-children-prop-is-reserved)
---------------------------------------------------------------

Content inside component tags becomes a snippet prop called `children`. You cannot have a separate prop by that name.

Breaking changes in runes mode[](#Breaking-changes-in-runes-mode)
-----------------------------------------------------------------

Some breaking changes only apply once your component is in runes mode.

### Bindings to component exports are not allowed[](#Breaking-changes-in-runes-mode-Bindings-to-component-exports-are-not-allowed)

Exports from runes mode components cannot be bound to directly. For example, having `export const foo = ...` in component `A` and then doing `<A bind:foo />` causes an error. Use `bind:this` instead — `<A bind:this={a} />` — and access the export as `a.foo`. This change makes things easier to reason about, as it enforces a clear separation between props and exports.

### Bindings need to be explicitly defined using $bindable()[](#Breaking-changes-in-runes-mode-Bindings-need-to-be-explicitly-defined-using-$bindable())

In Svelte 4 syntax, every property (declared via `export let`) is bindable, meaning you can `bind:` to it. In runes mode, properties are not bindable by default: you need to denote bindable props with the `$bindable` rune.

If a bindable property has a default value (e.g. `let { foo = $bindable('bar') } = $props();`), you need to pass a non-`undefined` value to that property if you’re binding to it. This prevents ambiguous behavior — the parent and child must have the same value — and results in better performance (in Svelte 4, the default value was reflected back to the parent, resulting in wasteful additional render cycles).

### accessors option is ignored[](#Breaking-changes-in-runes-mode-accessors-option-is-ignored)

Setting the `accessors` option to `true` makes properties of a component directly accessible on the component instance.

    <svelte:options accessors={true} />

    <script>
    	// available via componentInstance.name
    	export let name;
    </script>

In runes mode, properties are never accessible on the component instance. You can use component exports instead if you need to expose them.

    <script>
    	let { name } = $props();
    	// available via componentInstance.getName()
    	export const getName = () => name;
    </script>

Alternatively, if the place where they are instantiated is under your control, you can also make use of runes inside `.js/.ts` files by adjusting their ending to include `.svelte`, i.e. `.svelte.js` or `.svelte.ts`, and then use `$state`:

    import { function mount<Props extends Record<string, any>, Exports extends Record<string, any>>(component: ComponentType<SvelteComponent<Props>> | Component<Props, Exports, any>, options: MountOptions<Props>): ExportsMounts a component to the given target and returns the exports and potentially the props (if compiled with accessors: true) of the component.
    Transitions will play during the initial render unless the intro option is set to false.
    mount } from 'svelte';
    import type App = SvelteComponent<Record<string, any>, any, any>
    const App: LegacyComponentTypeApp from './App.svelte'

    const app = new App({ target: document.getElementById("app"), props: { foo: 'bar' } });
    app.foo = 'baz'
    const const props: {
        foo: string;
    }props = function $state<{
        foo: string;
    }>(initial: {
        foo: string;
    }): {
        foo: string;
    } (+1 overload)
    namespace $stateDeclares reactive state.
    Example:
    let count = $state(0);https://svelte.dev/docs/svelte/$state
    @paraminitial The initial value$state({ foo: stringfoo: 'bar' });
    const const app: {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<string, any>app = mount<Record<string, any>, {
        $on?(type: string, callback: (e: any) => void): () => void;
        $set?(props: Partial<Record<string, any>>): void;
    } & Record<...>>(component: ComponentType<...> | Component<...>, options: MountOptions<...>): {
        ...;
    } & Record<...>Mounts a component to the given target and returns the exports and potentially the props (if compiled with accessors: true) of the component.
    Transitions will play during the initial render unless the intro option is set to false.
    mount(const App: LegacyComponentTypeApp, { target: Document | Element | ShadowRootTarget element where the component will be mounted.
    target: var document: DocumentMDN Reference
    document.Document.getElementById(elementId: string): HTMLElement | nullReturns a reference to the first object with the specified value of the ID attribute.
    @paramelementId String that specifies the ID value.getElementById("app"), props?: Record<string, any> | undefinedComponent properties.
    props });
    const props: {
        foo: string;
    }props.foo: stringfoo = 'baz';

### immutable option is ignored[](#Breaking-changes-in-runes-mode-immutable-option-is-ignored)

Setting the `immutable` option has no effect in runes mode. This concept is replaced by how `$state` and its variations work.

### Classes are no longer “auto-reactive”[](#Breaking-changes-in-runes-mode-Classes-are-no-longer-auto-reactive)

In Svelte 4, doing the following triggered reactivity:

    <script>
    	let foo = new Foo();
    </script>

    <button on:click={() => (foo.value = 1)}>{foo.value}</button
    >

This is because the Svelte compiler treated the assignment to `foo.value` as an instruction to update anything that referenced `foo`. In Svelte 5, reactivity is determined at runtime rather than compile time, so you should define `value` as a reactive `$state` field on the `Foo` class. Wrapping `new Foo()` with `$state(...)` will have no effect — only vanilla objects and arrays are made deeply reactive.

### Touch and wheel events are passive[](#Breaking-changes-in-runes-mode-Touch-and-wheel-events-are-passive)

When using `onwheel`, `onmousewheel`, `ontouchstart` and `ontouchmove` event attributes, the handlers are [passive](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#using_passive_listeners) to align with browser defaults. This greatly improves responsiveness by allowing the browser to scroll the document immediately, rather than waiting to see if the event handler calls `event.preventDefault()`.

In the very rare cases that you need to prevent these event defaults, you should use [`on`](/docs/svelte/svelte-events#on) instead (for example inside an action).

### Attribute/prop syntax is stricter[](#Breaking-changes-in-runes-mode-Attribute-prop-syntax-is-stricter)

In Svelte 4, complex attribute values needn’t be quoted:

    <Component prop=this{is}valid />

This is a footgun. In runes mode, if you want to concatenate stuff you must wrap the value in quotes:

    <Component prop="this{is}valid" />

Note that Svelte 5 will also warn if you have a single expression wrapped in quotes, like `answer="{42}"` — in Svelte 6, that will cause the value to be converted to a string, rather than passed as a number.

### HTML structure is stricter[](#Breaking-changes-in-runes-mode-HTML-structure-is-stricter)

In Svelte 4, you were allowed to write HTML code that would be repaired by the browser when server side rendering it. For example you could write this...

    <table>
    	<tr>
    		<td>hi</td>
    	</tr>
    </table>

... and the browser would auto-insert a `<tbody>` element:

    <table>
    	<tbody>
    		<tr>
    			<td>hi</td>
    		</tr>
    	</tbody>
    </table>

Svelte 5 is more strict about the HTML structure and will throw a compiler error in cases where the browser would repair the DOM.

Other breaking changes[](#Other-breaking-changes)
-------------------------------------------------

### Stricter @const assignment validation[](#Other-breaking-changes-Stricter-const-assignment-validation)

Assignments to destructured parts of a `@const` declaration are no longer allowed. It was an oversight that this was ever allowed.

### :is(...) and :where(...) are scoped[](#Other-breaking-changes-:is()-and-:where()-are-scoped)

Previously, Svelte did not analyse selectors inside `:is(...)` and `:where(...)`, effectively treating them as global. Svelte 5 analyses them in the context of the current component. As such, some selectors may now be treated as unused if they were relying on this treatment. To fix this, use `:global(...)` inside the `:is(...)/:where(...)` selectors.

When using Tailwind’s `@apply` directive, add a `:global` selector to preserve rules that use Tailwind-generated `:is(...)` selectors:

    main :global {
    	@apply bg-blue-100 dark:bg-blue-900;
    }

### CSS hash position no longer deterministic[](#Other-breaking-changes-CSS-hash-position-no-longer-deterministic)

Previously Svelte would always insert the CSS hash last. This is no longer guaranteed in Svelte 5. This is only breaking if you [have very weird css selectors](https://stackoverflow.com/questions/15670631/does-the-order-of-classes-listed-on-an-item-affect-the-css).

### Scoped CSS uses :where(...)[](#Other-breaking-changes-Scoped-CSS-uses-:where())

To avoid issues caused by unpredictable specificity changes, scoped CSS selectors now use `:where(.svelte-xyz123)` selector modifiers alongside `.svelte-xyz123` (where `xyz123` is, as previously, a hash of the `<style>` contents). You can read more detail [here](https://github.com/sveltejs/svelte/pull/10443).

In the event that you need to support ancient browsers that don’t implement `:where`, you can manually alter the emitted CSS, at the cost of unpredictable specificity changes:

    css = css.replace(/:where\((.+?)\)/, '$1');



### Error/warning codes have been renamed[](#Other-breaking-changes-Error-warning-codes-have-been-renamed)

Error and warning codes have been renamed. Previously they used dashes to separate the words, they now use underscores (e.g. foo-bar becomes foo\_bar). Additionally, a handful of codes have been reworded slightly.

### Reduced number of namespaces[](#Other-breaking-changes-Reduced-number-of-namespaces)

The number of valid namespaces you can pass to the compiler option `namespace` has been reduced to `html` (the default), `mathml` and `svg`.

The `foreign` namespace was only useful for Svelte Native, which we’re planning to support differently in a 5.x minor.

### beforeUpdate/afterUpdate changes[](#Other-breaking-changes-beforeUpdate-afterUpdate-changes)

`beforeUpdate` no longer runs twice on initial render if it modifies a variable referenced in the template.

`afterUpdate` callbacks in a parent component will now run after `afterUpdate` callbacks in any child components.

`beforeUpdate/afterUpdate` no longer run when the component contains a `<slot>` and its content is updated.

Both functions are disallowed in runes mode — use `$effect.pre(...)` and `$effect(...)` instead.

### contenteditable behavior change[](#Other-breaking-changes-contenteditable-behavior-change)

If you have a `contenteditable` node with a corresponding binding _and_ a reactive value inside it (example: `<div contenteditable=true bind:textContent>count is {count}</div>`), then the value inside the contenteditable will not be updated by updates to `count` because the binding takes full control over the content immediately and it should only be updated through it.

### oneventname attributes no longer accept string values[](#Other-breaking-changes-oneventname-attributes-no-longer-accept-string-values)

In Svelte 4, it was possible to specify event attributes on HTML elements as a string:

    <button onclick="alert('hello')">...</button>

This is not recommended, and is no longer possible in Svelte 5, where properties like `onclick` replace `on:click` as the mechanism for adding event handlers.

### null and undefined become the empty string[](#Other-breaking-changes-null-and-undefined-become-the-empty-string)

In Svelte 4, `null` and `undefined` were printed as the corresponding string. In 99 out of 100 cases you want this to become the empty string instead, which is also what most other frameworks out there do. Therefore, in Svelte 5, `null` and `undefined` become the empty string.

### bind:files values can only be null, undefined or FileList[](#Other-breaking-changes-bind:files-values-can-only-be-null-undefined-or-FileList)

`bind:files` is now a two-way binding. As such, when setting a value, it needs to be either falsy (`null` or `undefined`) or of type `FileList`.

### Bindings now react to form resets[](#Other-breaking-changes-Bindings-now-react-to-form-resets)

Previously, bindings did not take into account `reset` event of forms, and therefore values could get out of sync with the DOM. Svelte 5 fixes this by placing a `reset` listener on the document and invoking bindings where necessary.

### walk no longer exported[](#Other-breaking-changes-walk-no-longer-exported)

`svelte/compiler` reexported `walk` from `estree-walker` for convenience. This is no longer true in Svelte 5, import it directly from that package instead in case you need it.

### Content inside svelte:options is forbidden[](#Other-breaking-changes-Content-inside-svelte:options-is-forbidden)

In Svelte 4 you could have content inside a `<svelte:options />` tag. It was ignored, but you could write something in there. In Svelte 5, content inside that tag is a compiler error.

### <slot> elements in declarative shadow roots are preserved[](#Other-breaking-changes-slot-elements-in-declarative-shadow-roots-are-preserved)

Svelte 4 replaced the `<slot />` tag in all places with its own version of slots. Svelte 5 preserves them in the case they are a child of a `<template shadowrootmode="...">` element.

### <svelte:element> tag must be an expression[](#Other-breaking-changes-svelte:element-tag-must-be-an-expression)

In Svelte 4, `<svelte:element this="div">` is valid code. This makes little sense — you should just do `<div>`. In the vanishingly rare case that you _do_ need to use a literal value for some reason, you can do this:

    <svelte:element this={"div"}>

Note that whereas Svelte 4 would treat `<svelte:element this="input">` (for example) identically to `<input>` for the purposes of determining which `bind:` directives could be applied, Svelte 5 does not.

### mount plays transitions by default[](#Other-breaking-changes-mount-plays-transitions-by-default)

The `mount` function used to render a component tree plays transitions by default unless the `intro` option is set to `false`. This is different from legacy class components which, when manually instantiated, didn’t play transitions by default.

### <img src={...}> and {@html ...} hydration mismatches are not repaired[](#Other-breaking-changes-img-src-and-html-hydration-mismatches-are-not-repaired)

In Svelte 4, if the value of a `src` attribute or `{@html ...}` tag differ between server and client (a.k.a. a hydration mismatch), the mismatch is repaired. This is very costly: setting a `src` attribute (even if it evaluates to the same thing) causes images and iframes to be reloaded, and reinserting a large blob of HTML is slow.

Since these mismatches are extremely rare, Svelte 5 assumes that the values are unchanged, but in development will warn you if they are not. To force an update you can do something like this:

    <script>
    	let { markup, src } = $props();

    	if (typeof window !== 'undefined') {
    		// stash the values...
    		const initial = { markup, src };

    		// unset them...
    		markup = src = undefined;

    		$effect(() => {
    			// ...and reset after we've mounted
    			markup = initial.markup;
    			src = initial.src;
    		});
    	}
    </script>

    {@html markup}
    <img {src} />

### Hydration works differently[](#Other-breaking-changes-Hydration-works-differently)

Svelte 5 makes use of comments during server side rendering which are used for more robust and efficient hydration on the client. As such, you shouldn’t remove comments from your HTML output if you intend to hydrate it, and if you manually authored HTML to be hydrated by a Svelte component, you need to adjust that HTML to include said comments at the correct positions.

### onevent attributes are delegated[](#Other-breaking-changes-onevent-attributes-are-delegated)

Event attributes replace event directives: Instead of `on:click={handler}` you write `onclick={handler}`. For backwards compatibility the `on:event` syntax is still supported and behaves the same as in Svelte 4. Some of the `onevent` attributes however are delegated, which means you need to take care to not stop event propagation on those manually, as they then might never reach the listener for this event type at the root.

### \--style-props uses a different element[](#Other-breaking-changes-style-props-uses-a-different-element)

Svelte 5 uses an extra `<svelte-css-wrapper>` element instead of a `<div>` to wrap the component when using CSS custom properties.