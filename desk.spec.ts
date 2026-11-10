import {test,expect} from '@playwright/test';
test('create, persist, search, update and filter a ticket',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.getByText('Loading requests…')).toHaveCount(0);
 await page.getByRole('button',{name:'+ New ticket'}).click();
 await page.getByLabel('Title',{exact:true}).fill('Synthetic keyboard test');
 await page.getByLabel('Description',{exact:true}).fill('A fictional issue for automated browser verification.');
 await page.getByLabel('Category',{exact:true}).selectOption('Product');
 await page.getByLabel('Priority',{exact:true}).selectOption('High');
 await page.getByRole('button',{name:'Create ticket',exact:true}).click();
 await expect(page.getByRole('dialog')).toBeVisible();
 await page.getByLabel('Update status').selectOption('In progress');
 await expect(page.getByText('Status saved to SQLite.')).toBeAttached();
 await page.getByRole('button',{name:'Back to queue'}).click();
 await page.reload();await page.getByLabel('Search requests').fill('Synthetic keyboard test');
 await expect(page.getByRole('button',{name:/Synthetic keyboard test/})).toHaveCount(1);
 await page.getByRole('button',{name:'Resolved',exact:true}).click();
 await expect(page.getByText('No matching requests')).toBeVisible();
 expect(errors).toEqual([]);
});
test('responsive queue has no horizontal overflow at 320,390,1280',async({page})=>{
 for(const w of [320,390,1280]){await page.setViewportSize({width:w,height:900});await page.goto('/');await expect(page.getByRole('heading',{name:'Request queue'})).toBeVisible();await expect(page.locator('.ticket').first()).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`evidence/queue-${w}.png`,fullPage:true});}
});
test('modal keyboard focus stays inside and Escape closes',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'+ New ticket'}).click();
 await expect(page.getByRole('button',{name:'Close form'})).toBeFocused();
 await page.keyboard.press('Shift+Tab');await expect(page.getByRole('button',{name:'Create ticket',exact:true})).toBeFocused();
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
});
test('HTML-looking ticket title is rendered as text, not markup',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'+ New ticket'}).click();
 await page.getByLabel('Title',{exact:true}).fill('<img src=x onerror=alert(1)>');
 await page.getByLabel('Description',{exact:true}).fill('Synthetic injection safety regression example.');
 await page.getByRole('button',{name:'Create ticket',exact:true}).click();
 await expect(page.getByRole('heading',{name:'<img src=x onerror=alert(1)>'})).toBeVisible();
 await expect(page.locator('.dialog img')).toHaveCount(0);
});

test('busy save cannot dismiss modal and backdrop locks document scroll',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'+ New ticket'}).click();
 await expect(page.locator('body')).toHaveCSS('overflow','hidden');
 await page.getByLabel('Title',{exact:true}).fill('Synthetic busy save');await page.getByLabel('Description',{exact:true}).fill('Fictional delayed request for keyboard regression.');
 let release:()=>void=()=>{};const barrier=new Promise<void>(r=>release=r);
 await page.route('**/api/tickets',async route=>{if(route.request().method()==='POST'){await barrier;}await route.continue();});
 await page.getByRole('button',{name:'Create ticket',exact:true}).click();await expect(page.getByRole('button',{name:'Saving…'})).toBeDisabled();
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toBeVisible();await expect(page.getByRole('button',{name:'Close form'})).toBeDisabled();release();
 await expect(page.getByRole('heading',{name:'Synthetic busy save'})).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.locator('body')).not.toHaveCSS('overflow','hidden');
});
